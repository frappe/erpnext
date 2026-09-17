# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.doctype.warehouse.warehouse import get_warehouses_based_on_account
from erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison import (
	create_gl_reposting_entries,
	create_reposting_entries,
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite

PI_COMPANY = "_Test Company with perpetual inventory"
PI_STORES = "Stores - TCP1"


class TestStockAndAccountValueComparison(ERPNextTestSuite):
	def test_purchase_voucher_reposted_transaction_based(self):
		# A Purchase Receipt whose GL entries are missing must surface in the report and, when reposted
		# from it, be reposted Transaction-based (so its own GL is regenerated) rather than the slower
		# Item-and-Warehouse based reposting.
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		pr = make_purchase_receipt(item_code=item, company=PI_COMPANY, warehouse=PI_STORES, qty=5, rate=100)

		# Simulate the out-of-sync state: stock ledger exists but the accounting ledger does not.
		frappe.db.delete("GL Entry", {"voucher_type": "Purchase Receipt", "voucher_no": pr.name})

		# The receipt now shows up in the comparison report (stock value 500 vs account value 0).
		filters = frappe._dict(company=PI_COMPANY, as_on_date=today())
		_columns, data = execute(filters)

		row = next((d for d in data if d.get("voucher_no") == pr.name), None)
		self.assertIsNotNone(row, "Out-of-sync Purchase Receipt should appear in the report")
		self.assertEqual(row.get("voucher_type"), "Purchase Receipt")

		# Repost from the report.
		create_reposting_entries([row], PI_COMPANY)

		# A Transaction-based Repost Item Valuation must have been created for this voucher...
		transaction_rivs = frappe.get_all(
			"Repost Item Valuation",
			filters={"voucher_no": pr.name, "voucher_type": "Purchase Receipt"},
			fields=["name", "based_on"],
		)

		self.assertTrue(transaction_rivs, "Expected a Repost Item Valuation for the Purchase Receipt")
		self.assertTrue(all(riv.based_on == "Transaction" for riv in transaction_rivs))

		# ...and no Item-and-Warehouse based reposting should have been created for this item.
		item_wh_rivs = frappe.get_all(
			"Repost Item Valuation",
			filters={"based_on": "Item and Warehouse", "item_code": item},
		)
		self.assertFalse(item_wh_rivs, "Purchase vouchers must not be reposted Item-and-Warehouse based")

	def test_child_account_override_excluded_from_group_account(self):
		# A group warehouse carries an inventory account; a child (e.g. Goods-in-Transit) can override
		# it with its own account. get_warehouses_based_on_account must return only warehouses whose
		# effective account matches, excluding the overriding child.
		group = create_warehouse("_Test SAVC Group WH", {"is_group": 1}, company=PI_COMPANY)
		group_account = frappe.get_value("Warehouse", group, "account")

		inheriting = create_warehouse(
			"_Test SAVC Inherit WH", {"parent_warehouse": group, "account": group_account}, company=PI_COMPANY
		)
		overriding = create_warehouse(
			"_Test SAVC Transit WH", {"parent_warehouse": group}, company=PI_COMPANY
		)

		warehouses = get_warehouses_based_on_account(group_account, PI_COMPANY)

		self.assertIn(inheriting, warehouses)
		self.assertNotIn(overriding, warehouses)

	def test_gl_reposting_only_repost_accounting_ledgers(self):
		# When the stock ledger is correct but the accounting ledger has drifted, the report can queue a
		# repost that touches only the accounting ledgers, leaving stock valuation alone.
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		pr = make_purchase_receipt(item_code=item, company=PI_COMPANY, warehouse=PI_STORES, qty=5, rate=100)

		frappe.db.delete("GL Entry", {"voucher_type": "Purchase Receipt", "voucher_no": pr.name})

		filters = frappe._dict(company=PI_COMPANY, as_on_date=today())
		_columns, data = execute(filters)

		row = next((d for d in data if d.get("voucher_no") == pr.name), None)
		self.assertIsNotNone(row, "Out-of-sync Purchase Receipt should appear in the report")

		create_gl_reposting_entries([row], PI_COMPANY)

		rivs = frappe.get_all(
			"Repost Item Valuation",
			filters={"voucher_no": pr.name, "voucher_type": "Purchase Receipt"},
			fields=["name", "based_on", "repost_only_accounting_ledgers"],
		)

		self.assertEqual(len(rivs), 1)
		self.assertEqual(rivs[0].based_on, "Transaction")
		self.assertTrue(rivs[0].repost_only_accounting_ledgers)

		# Reposts run inline during tests, so the missing accounting entries must be back.
		self.assertTrue(
			frappe.db.exists("GL Entry", {"voucher_type": "Purchase Receipt", "voucher_no": pr.name})
		)

	def test_gl_reposting_skips_already_queued_voucher(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		pr = make_purchase_receipt(item_code=item, company=PI_COMPANY, warehouse=PI_STORES, qty=5, rate=100)

		row = {
			"ledger_type": "Stock Ledger Entry",
			"voucher_type": "Purchase Receipt",
			"voucher_no": pr.name,
			"posting_date": pr.posting_date,
			"posting_time": pr.posting_time,
		}

		# The same voucher selected twice, and then selected again on a second run, must not pile up
		# duplicate reposting entries.
		frappe.flags.dont_execute_stock_reposts = True
		try:
			create_gl_reposting_entries([row, dict(row)], PI_COMPANY)
			create_gl_reposting_entries([row], PI_COMPANY)
		finally:
			frappe.flags.dont_execute_stock_reposts = False

		rivs = frappe.get_all(
			"Repost Item Valuation",
			filters={
				"voucher_no": pr.name,
				"voucher_type": "Purchase Receipt",
				"repost_only_accounting_ledgers": 1,
			},
		)

		self.assertEqual(len(rivs), 1)

	def test_gl_reposting_not_allowed_for_gl_entry_rows(self):
		# Rows of ledger type "GL Entry" have no stock ledger entries to rebuild the accounting ledgers
		# from, so a GL-only repost must be refused instead of wiping their GL entries.
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		pr = make_purchase_receipt(item_code=item, company=PI_COMPANY, warehouse=PI_STORES, qty=5, rate=100)

		frappe.db.delete("Stock Ledger Entry", {"voucher_type": "Purchase Receipt", "voucher_no": pr.name})

		filters = frappe._dict(company=PI_COMPANY, as_on_date=today())
		_columns, data = execute(filters)

		row = next((d for d in data if d.get("voucher_no") == pr.name), None)
		self.assertIsNotNone(row, "Purchase Receipt without stock ledgers should appear in the report")
		self.assertEqual(row.get("ledger_type"), "GL Entry")

		self.assertRaises(frappe.ValidationError, create_gl_reposting_entries, [row], PI_COMPANY)

		self.assertFalse(
			frappe.db.exists(
				"Repost Item Valuation", {"voucher_no": pr.name, "voucher_type": "Purchase Receipt"}
			)
		)

	def test_gl_reposting_not_allowed_against_gl_entry_voucher_type(self):
		# Guard on the Repost Item Valuation itself, for anything creating one outside the report.
		riv = frappe.new_doc("Repost Item Valuation")
		riv.update(
			{
				"based_on": "Transaction",
				"voucher_type": "GL Entry",
				"voucher_no": "some-gl-entry",
				"posting_date": today(),
				"company": PI_COMPANY,
				"repost_only_accounting_ledgers": 1,
			}
		)

		self.assertRaises(frappe.ValidationError, riv.validate_repost_only_accounting_ledgers)

		riv.repost_only_accounting_ledgers = 0
		riv.validate_repost_only_accounting_ledgers()

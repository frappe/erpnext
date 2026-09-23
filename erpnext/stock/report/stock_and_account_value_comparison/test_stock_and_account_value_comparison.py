# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.doctype.warehouse.warehouse import get_warehouses_based_on_account
from erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison import (
	create_gl_reposting_entries,
	create_reposting_entries,
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company with perpetual inventory"
PI_STORES = "Stores - TCP1"


class TestStockAndAccountValueComparison(ERPNextTestSuite):
	def test_balanced_warehouse_not_flagged(self):
		warehouse = create_warehouse("_Test SAVC WH", company=COMPANY)
		account = frappe.get_value("Warehouse", warehouse, "account")
		item = "_Test Item"

		make_stock_entry(
			item_code=item,
			to_warehouse=warehouse,
			qty=10,
			rate=100,
			company=COMPANY,
			posting_date="2026-06-01",
		)

		# Filtering by the isolated account restricts both the stock-ledger and GL
		# scans to this fresh warehouse's account only.
		rows = self.run_report(account=account)

		# The report lists only mismatches (rows where abs(difference_value) > 0.1),
		# keyed per voucher. A balanced perpetual warehouse posts equal stock-ledger
		# and GL values for the receipt voucher, so nothing should be flagged.
		self.assertEqual(rows, [])

	def test_stock_account_gl_mismatch_is_flagged(self):
		warehouse = create_warehouse("_Test SAVC Mismatch WH", company=COMPANY)
		account = frappe.get_value("Warehouse", warehouse, "account")

		receipt = make_stock_entry(
			item_code="_Test Item",
			to_warehouse=warehouse,
			qty=10,
			rate=100,
			company=COMPANY,
			posting_date="2026-06-01",
		)

		# Simulate corruption: the stock-account GL entry for this receipt drifts out of sync
		# with the stock ledger (stock value stays 1000, but the account only shows 600).
		frappe.db.set_value(
			"GL Entry",
			{"voucher_no": receipt.name, "account": account, "is_cancelled": 0},
			"debit_in_account_currency",
			600,
			update_modified=False,
		)

		rows = self.run_report(account=account)

		row = next((r for r in rows if r["voucher_no"] == receipt.name), None)
		self.assertIsNotNone(row, "Tampered GL entry should cause the voucher to appear in the report")
		self.assertEqual(row["ledger_type"], "Stock Ledger Entry")
		self.assertEqual(row["stock_value"], 1000)  # unchanged stock ledger value
		self.assertEqual(row["account_value"], 600)  # tampered GL value
		self.assertEqual(row["difference_value"], 400)  # 1000 - 600, above the 0.1 threshold

	def test_purchase_voucher_reposted_transaction_based(self):
		# A Purchase Receipt whose GL entries are missing must surface in the report and, when reposted
		# from it, be reposted Transaction-based (so its own GL is regenerated) rather than the slower
		# Item-and-Warehouse based reposting.
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		pr = make_purchase_receipt(item_code=item, company=COMPANY, warehouse=PI_STORES, qty=5, rate=100)

		# Simulate the out-of-sync state: stock ledger exists but the accounting ledger does not.
		frappe.db.delete("GL Entry", {"voucher_type": "Purchase Receipt", "voucher_no": pr.name})

		# The receipt now shows up in the comparison report (stock value 500 vs account value 0).
		filters = frappe._dict(company=COMPANY, as_on_date=today())
		_columns, data = execute(filters)

		row = next((d for d in data if d.get("voucher_no") == pr.name), None)
		self.assertIsNotNone(row, "Out-of-sync Purchase Receipt should appear in the report")
		self.assertEqual(row.get("voucher_type"), "Purchase Receipt")

		# Repost from the report.
		create_reposting_entries([row], COMPANY)

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
		group = create_warehouse("_Test SAVC Group WH", {"is_group": 1}, company=COMPANY)
		group_account = frappe.get_value("Warehouse", group, "account")

		inheriting = create_warehouse(
			"_Test SAVC Inherit WH", {"parent_warehouse": group, "account": group_account}, company=COMPANY
		)
		overriding = create_warehouse("_Test SAVC Transit WH", {"parent_warehouse": group}, company=COMPANY)

		warehouses = get_warehouses_based_on_account(group_account, COMPANY)

		self.assertIn(inheriting, warehouses)
		self.assertNotIn(overriding, warehouses)

	def test_gl_reposting_only_repost_accounting_ledgers(self):
		# When the stock ledger is correct but the accounting ledger has drifted, the report can queue a
		# repost that touches only the accounting ledgers, leaving stock valuation alone.
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		pr = make_purchase_receipt(item_code=item, company=COMPANY, warehouse=PI_STORES, qty=5, rate=100)

		frappe.db.delete("GL Entry", {"voucher_type": "Purchase Receipt", "voucher_no": pr.name})

		filters = frappe._dict(company=COMPANY, as_on_date=today())
		_columns, data = execute(filters)

		row = next((d for d in data if d.get("voucher_no") == pr.name), None)
		self.assertIsNotNone(row, "Out-of-sync Purchase Receipt should appear in the report")

		create_gl_reposting_entries([row], COMPANY, from_date=pr.posting_date)

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

		pr = make_purchase_receipt(item_code=item, company=COMPANY, warehouse=PI_STORES, qty=5, rate=100)

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
			create_gl_reposting_entries([row, dict(row)], COMPANY, from_date=pr.posting_date)
			create_gl_reposting_entries([row], COMPANY, from_date=pr.posting_date)
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

	def test_gl_reposting_skips_journal_entry_rows(self):
		# A Journal Entry posted straight to a stock account shows up in the report but has no stock
		# ledger entries, so it is skipped rather than blocking the whole selection.
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		pr = make_purchase_receipt(item_code=item, company=COMPANY, warehouse=PI_STORES, qty=5, rate=100)
		frappe.db.delete("GL Entry", {"voucher_type": "Purchase Receipt", "voucher_no": pr.name})

		filters = frappe._dict(company=COMPANY, as_on_date=today())
		_columns, data = execute(filters)
		pr_row = next((d for d in data if d.get("voucher_no") == pr.name), None)

		journal_row = {
			"ledger_type": "GL Entry",
			"voucher_type": "Journal Entry",
			"voucher_no": "_Test JE for GL Reposting",
			"posting_date": today(),
		}

		create_gl_reposting_entries([journal_row, pr_row], COMPANY, pr.posting_date)

		self.assertFalse(
			frappe.db.exists("Repost Item Valuation", {"voucher_type": "Journal Entry"}),
			"Journal Entry rows must be skipped",
		)
		self.assertTrue(frappe.db.exists("Repost Item Valuation", {"voucher_no": pr.name}))

	def test_gl_reposting_ignores_rows_posted_before_from_date(self):
		# Rows posted before the From Date must be dropped, so a stale selection cannot rewrite the
		# accounting ledgers of an already reconciled period.
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		old_pr = make_purchase_receipt(
			item_code=item,
			company=COMPANY,
			warehouse=PI_STORES,
			qty=5,
			rate=100,
			posting_date=add_days(today(), -10),
		)
		new_pr = make_purchase_receipt(item_code=item, company=COMPANY, warehouse=PI_STORES, qty=5, rate=100)

		rows = [
			{
				"ledger_type": "Stock Ledger Entry",
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"posting_date": pr.posting_date,
				"posting_time": pr.posting_time,
			}
			for pr in (old_pr, new_pr)
		]

		frappe.flags.dont_execute_stock_reposts = True
		try:
			create_gl_reposting_entries(rows, COMPANY, from_date=add_days(today(), -1))
		finally:
			frappe.flags.dont_execute_stock_reposts = False

		self.assertFalse(
			frappe.db.exists("Repost Item Valuation", {"voucher_no": old_pr.name}),
			"Row posted before the From Date must be ignored",
		)
		self.assertTrue(frappe.db.exists("Repost Item Valuation", {"voucher_no": new_pr.name}))

	def test_gl_reposting_skips_gl_only_rows(self):
		# The report's GL-only rows carry their real voucher type (eg. a Payment Entry posted to a stock
		# account), but without stock ledger entries there is nothing to rebuild the ledgers from.
		row = {
			"ledger_type": "GL Entry",
			"voucher_type": "Payment Entry",
			"voucher_no": "_Test PE for GL Reposting",
			"posting_date": today(),
		}

		create_gl_reposting_entries([row], COMPANY, from_date=today())

		self.assertFalse(frappe.db.exists("Repost Item Valuation", {"voucher_no": row["voucher_no"]}))

	def test_gl_reposting_uses_voucher_posting_date(self):
		# A row claiming a later posting date than the voucher really has must not get past the From
		# Date bound, and the repost is created with the voucher's own posting date.
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		old_pr = make_purchase_receipt(
			item_code=item,
			company=COMPANY,
			warehouse=PI_STORES,
			qty=5,
			rate=100,
			posting_date=add_days(today(), -10),
		)

		row = {
			"ledger_type": "Stock Ledger Entry",
			"voucher_type": "Purchase Receipt",
			"voucher_no": old_pr.name,
			"posting_date": today(),
			"posting_time": old_pr.posting_time,
		}

		frappe.flags.dont_execute_stock_reposts = True
		try:
			create_gl_reposting_entries([row], COMPANY, from_date=add_days(today(), -1))
			self.assertFalse(frappe.db.exists("Repost Item Valuation", {"voucher_no": old_pr.name}))

			create_gl_reposting_entries([row], COMPANY, from_date=add_days(today(), -20))
		finally:
			frappe.flags.dont_execute_stock_reposts = False

		posting_date = frappe.db.get_value(
			"Repost Item Valuation", {"voucher_no": old_pr.name}, "posting_date"
		)
		self.assertEqual(getdate(posting_date), getdate(old_pr.posting_date))

	def test_gl_reposting_requires_from_date(self):
		row = {
			"ledger_type": "Stock Ledger Entry",
			"voucher_type": "Purchase Receipt",
			"voucher_no": "some-receipt",
			"posting_date": today(),
		}

		self.assertRaises(frappe.ValidationError, create_gl_reposting_entries, [row], COMPANY, None)

	def test_gl_reposting_not_allowed_against_gl_entry_voucher_type(self):
		# Guard on the Repost Item Valuation itself, for anything creating one outside the report.
		riv = frappe.new_doc("Repost Item Valuation")
		riv.update(
			{
				"based_on": "Transaction",
				"voucher_type": "GL Entry",
				"voucher_no": "some-gl-entry",
				"posting_date": today(),
				"company": COMPANY,
				"repost_only_accounting_ledgers": 1,
			}
		)

		self.assertRaises(frappe.ValidationError, riv.validate_repost_only_accounting_ledgers)

		riv.repost_only_accounting_ledgers = 0
		riv.validate_repost_only_accounting_ledgers()

	def run_report(self, **extra):
		filters = {"company": COMPANY, "as_on_date": "2026-12-31"}
		filters.update(extra)
		return execute(frappe._dict(filters))[1]

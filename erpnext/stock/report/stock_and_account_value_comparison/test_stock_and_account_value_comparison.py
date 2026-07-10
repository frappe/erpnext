# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison import (
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

	def run_report(self, **extra):
		filters = {"company": COMPANY, "as_on_date": "2026-12-31"}
		filters.update(extra)
		return execute(frappe._dict(filters))[1]

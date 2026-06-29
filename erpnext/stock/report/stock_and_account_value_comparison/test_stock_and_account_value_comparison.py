# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison import (
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

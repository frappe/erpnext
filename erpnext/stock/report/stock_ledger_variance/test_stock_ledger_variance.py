# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestStockLedgerVariance(ERPNextTestSuite):
	def run_report(self, **extra):
		from erpnext.stock.report.stock_ledger_variance.stock_ledger_variance import execute

		filters = {"company": "_Test Company"}
		filters.update(extra)

		return execute(frappe._dict(filters))[1]

	def test_emptied_fifo_queue_is_reported_on_its_own_entry(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name
		warehouse = "Stores - _TC"
		for qty, rate, day in ((10, 100, 1), (10, 200, 2)):
			make_stock_entry(
				item_code=item, to_warehouse=warehouse, qty=qty, rate=rate, posting_date=f"2026-06-0{day}"
			)
		issues = [
			make_stock_entry(
				item_code=item, from_warehouse=warehouse, qty=qty, posting_date=f"2026-06-0{day}"
			)
			for qty, day in ((1, 3), (4, 4), (2, 5))
		]
		sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": issues[0].name}, "name")
		frappe.db.set_value("Stock Ledger Entry", sle, "stock_queue", "[]", update_modified=False)

		data = self.run_report(item_code=item, difference_in="Qty")

		self.assertEqual([row["name"] for row in data if row.get("item_code") == item], [sle])

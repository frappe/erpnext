# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.negative_batch_report.negative_batch_report import execute
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"
COMPANY = "_Test Company"


class TestNegativeBatchReport(ERPNextTestSuite):
	def run_report(self, item_code):
		filters = frappe._dict({"company": COMPANY, "warehouse": WAREHOUSE, "item_code": item_code})
		return execute(filters)[1]

	def make_batch_item(self):
		return make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "NBR-.#####",
			}
		).name

	def receive_batch(self, item, qty, posting_date):
		"""Receive `qty` of `item`, creating its batch, and return the batch no."""
		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=qty, rate=100, posting_date=posting_date)
		return frappe.get_all("Batch", filters={"item": item}, pluck="name")[0]

	def test_healthy_batch_not_negative(self):
		item = self.make_batch_item()
		batch = self.receive_batch(item, 10, "2026-06-01")
		# issue from the same batch, staying within its balance
		make_stock_entry(
			item_code=item, from_warehouse=WAREHOUSE, qty=4, batch_no=batch, posting_date="2026-06-02"
		)

		# received 10 then issued 4 -> running batch balance never goes negative
		data = self.run_report(item)
		self.assertFalse([row for row in data if row.get("batch_no") == batch])

	def test_negative_batch_is_flagged(self):
		# ERPNext blocks a negative batch balance at submission time (across several
		# layers), so a genuinely negative batch only exists as corrupt historical
		# data -- which is exactly what this report is meant to surface. Reproduce
		# that state directly by forcing the batch's ledger quantity below zero.
		item = self.make_batch_item()
		batch = self.receive_batch(item, 10, "2026-06-10")

		sle = frappe.get_all("Stock Ledger Entry", filters={"item_code": item}, pluck="name")[0]
		entry = frappe.get_all("Serial and Batch Entry", filters={"batch_no": batch}, pluck="name")[0]
		frappe.db.set_value("Serial and Batch Entry", entry, "qty", -3)
		frappe.db.set_value("Stock Ledger Entry", sle, {"actual_qty": -3, "qty_after_transaction": -3})

		data = self.run_report(item)
		flagged = [row for row in data if row.get("batch_no") == batch]
		self.assertEqual(len(flagged), 1, "A batch with a negative running balance must be flagged")
		self.assertEqual(flagged[0]["qty_after_transaction"], -3)
		self.assertEqual(flagged[0]["warehouse"], WAREHOUSE)

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.incorrect_serial_no_valuation.incorrect_serial_no_valuation import execute
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"


class TestIncorrectSerialNoValuation(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company"})
		filters.update(extra)
		return execute(filters)[1]

	def make_serial_item(self, series):
		return make_item(properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": series}).name

	def test_pre_period_receipt_is_included_when_validating_issue(self):
		item = self.make_serial_item("ISV-OPEN-.#####")

		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=1, rate=100, posting_date="2026-05-31")
		make_stock_entry(item_code=item, from_warehouse=WAREHOUSE, qty=1, posting_date="2026-06-01")

		data = self.run_report(from_date="2026-06-01", to_date="2026-06-30")

		flagged_items = {row.get("item_code") for row in data}
		self.assertNotIn(item, flagged_items)

	def test_period_discrepancy_uses_opening_balance_without_showing_history(self):
		item = self.make_serial_item("ISV-BAD-.#####")

		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=1, rate=100, posting_date="2026-05-31")
		serial_no = frappe.get_all("Serial No", filters={"item_code": item}, pluck="name")[0]
		make_stock_entry(item_code=item, from_warehouse=WAREHOUSE, qty=1, posting_date="2026-06-01")
		frappe.db.set_value(
			"Serial and Batch Entry",
			{"serial_no": serial_no, "qty": ["<", 0]},
			"incoming_rate",
			60,
			update_modified=False,
		)

		data = self.run_report(item_code=item, from_date="2026-06-01", to_date="2026-06-30")

		details = [row for row in data if row.get("posting_date")]
		self.assertEqual(len(details), 1)
		self.assertEqual(details[0].serial_no, serial_no)
		self.assertEqual(str(details[0].posting_date), "2026-06-01")
		self.assertEqual(data[-1].qty, 0)
		self.assertEqual(data[-1].valuation_rate, 40)

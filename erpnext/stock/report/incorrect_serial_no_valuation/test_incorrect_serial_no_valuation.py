# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.incorrect_serial_no_valuation.incorrect_serial_no_valuation import execute
from erpnext.tests.utils import ERPNextTestSuite

SERIAL_ITEM = "_Test Serialized Item With Series"
WAREHOUSE = "Stores - _TC"


class TestIncorrectSerialNoValuation(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company"})
		filters.update(extra)
		return execute(filters)[1]

	def test_healthy_serial_item_not_flagged(self):
		make_stock_entry(
			item_code=SERIAL_ITEM,
			to_warehouse=WAREHOUSE,
			qty=3,
			rate=100,
			posting_date="2026-06-01",
		)
		make_stock_entry(
			item_code=SERIAL_ITEM,
			from_warehouse=WAREHOUSE,
			qty=1,
			posting_date="2026-06-02",
		)

		data = self.run_report(item_code=SERIAL_ITEM)

		flagged_items = {row.get("item_code") for row in data if isinstance(row, dict)}
		self.assertNotIn(SERIAL_ITEM, flagged_items)

	def test_only_balance_row_when_filtered_to_healthy_item(self):
		make_stock_entry(
			item_code=SERIAL_ITEM,
			to_warehouse=WAREHOUSE,
			qty=3,
			rate=100,
			posting_date="2026-06-01",
		)

		data = self.run_report(item_code=SERIAL_ITEM)

		# The report always appends a single "Balance" summary row. A healthy
		# serial item contributes no detail rows, so only that summary remains.
		self.assertEqual(len(data), 1)
		self.assertEqual(data[-1].get("qty"), 0)
		self.assertEqual(data[-1].get("valuation_rate"), 0)

	def test_mismatched_in_out_valuation_is_flagged(self):
		# fresh serial item so only this test's serial movements are considered
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "ISV-BAD-.#####"}
		).name

		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=1, rate=100, posting_date="2026-06-01")
		serial_no = frappe.get_all("Serial No", filters={"item_code": item}, pluck="name")[0]
		make_stock_entry(item_code=item, from_warehouse=WAREHOUSE, qty=1, posting_date="2026-06-02")

		# corrupt the outgoing valuation so the serial's in (100) and out no longer cancel:
		# net qty is 0 but a residual value remains, which the report must flag
		frappe.db.set_value(
			"Serial and Batch Entry",
			{"serial_no": serial_no, "qty": ["<", 0]},
			"incoming_rate",
			60,
			update_modified=False,
		)

		data = self.run_report(item_code=item)

		flagged_serials = {row.get("serial_no") for row in data if isinstance(row, dict)}
		self.assertIn(serial_no, flagged_serials)

import frappe
from frappe import _dict
from frappe.utils import today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.serial_and_batch_wise_stock_balance.serial_and_batch_wise_stock_balance import (
	SerialAndBatchWiseStockBalanceReport,
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"
RECEIVE = {"rate": 100, "to_warehouse": WAREHOUSE}
ISSUE = {"from_warehouse": WAREHOUSE}


class TestSerialAndBatchWiseStockBalance(ERPNextTestSuite):
	def run_report(self, properties, movements, include_zero_stock_items=0):
		item_code = make_item(properties={"is_stock_item": 1, **properties}).name
		for movement in movements:
			make_stock_entry(item_code=item_code, **movement)

		filters = _dict(
			company="_Test Company",
			item_code=[item_code],
			warehouse=WAREHOUSE,
			from_date="2020-01-01",
			to_date=today(),
			include_zero_stock_items=include_zero_stock_items,
		)
		return [_dict(row) for row in execute(filters)[1]]

	def get_serial_nos_in_warehouse(self, item_code, batch_no=None):
		filters = {"item_code": item_code, "warehouse": WAREHOUSE}
		if batch_no:
			filters["batch_no"] = batch_no

		return "\n".join(sorted(frappe.get_all("Serial No", filters=filters, pluck="name")))

	def test_batch_rows_under_item_row(self):
		rows = self.run_report(
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SBW-B-.#####"},
			[{"qty": 10, **RECEIVE}, {"qty": 20, **RECEIVE}, {"qty": 5, **ISSUE}],
		)

		self.assertEqual(
			[(row.indent, row.in_qty, row.out_qty, row.bal_qty, row.bal_val) for row in rows],
			[(0, 30, 5, 25, 2500), (1, 10, 5, 5, 500), (1, 20, 0, 20, 2000)],
		)
		self.assertTrue(all(row.batch_no for row in rows[1:]))
		self.assertEqual(rows[0].batch_no, f"{rows[1].batch_no}\n{rows[2].batch_no}")

	def test_item_row_lists_the_batches_under_it(self):
		rows = self.run_report(
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SBW-Z-.#####"},
			[{"qty": 10, **RECEIVE}, {"qty": 10, **ISSUE}, {"qty": 5, **RECEIVE}],
			include_zero_stock_items=1,
		)

		self.assertEqual([row.bal_qty for row in rows], [5, 0, 5])
		self.assertEqual(rows[0].batch_no, f"{rows[1].batch_no}\n{rows[2].batch_no}")

	def test_serial_nos_in_stock_on_item_row(self):
		rows = self.run_report(
			{"has_serial_no": 1, "serial_no_series": "SBW-S-.#####"},
			[{"qty": 3, **RECEIVE}, {"qty": 1, **ISSUE}],
		)

		self.assertEqual(len(rows), 1)
		self.assertEqual(len(rows[0].serial_no.split("\n")), 2)
		self.assertEqual(rows[0].serial_no, self.get_serial_nos_in_warehouse(rows[0].item_code))

	def test_serial_nos_in_stock_per_batch(self):
		rows = self.run_report(
			{
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SBW-SB-.#####",
				"has_serial_no": 1,
				"serial_no_series": "SBW-SBS-.#####",
			},
			[{"qty": 2, **RECEIVE}, {"qty": 2, **RECEIVE}, {"qty": 1, **ISSUE}],
		)

		self.assertEqual([row.bal_qty for row in rows], [3, 1, 2])
		self.assertEqual(rows[0].batch_no, f"{rows[1].batch_no}\n{rows[2].batch_no}")
		self.assertEqual(rows[0].serial_no, self.get_serial_nos_in_warehouse(rows[0].item_code))
		for row in rows[1:]:
			self.assertEqual(row.serial_no, self.get_serial_nos_in_warehouse(row.item_code, row.batch_no))

	def test_batch_rows_carry_item_row_dimensions(self):
		report = SerialAndBatchWiseStockBalanceReport(
			_dict(company="_Test Company", from_date=today(), to_date=today(), show_dimension_wise_stock=1)
		)
		report.inventory_dimensions = ["project"]
		report.serial_map = {}
		report.batch_map = {
			("SBW Item", WAREHOUSE, "SBW Project"): {"SBW Batch": _dict(bal_qty=5, bal_val=500)}
		}
		item_row = _dict(
			item_code="SBW Item", warehouse=WAREHOUSE, project="SBW Project", bal_qty=5, bal_val=500
		)

		batch_row = report.get_item_and_batch_rows(item_row)[1]

		self.assertEqual((batch_row.batch_no, batch_row.project), ("SBW Batch", "SBW Project"))

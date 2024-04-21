import datetime

import frappe
from frappe import _dict
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import add_to_date, getdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_analytics.stock_analytics import execute, get_period_date_ranges


def stock_analytics(filters):
	col, data, *_ = execute(filters)
	return col, data


class TestStockAnalyticsReport(FrappeTestCase):
	def setUp(self) -> None:
		self.item = make_item().name
		self.warehouse = "_Test Warehouse - _TC"

	def assert_single_item_report(self, movement, expected_buckets):
		self.generate_stock(movement)
		filters = _dict(
			range="Monthly",
			from_date=movement[0][1].replace(day=1),
			to_date=movement[-1][1].replace(day=28),
			value_quantity="Quantity",
			company="_Test Company",
			item_code=self.item,
		)

		cols, data = stock_analytics(filters)

		self.assertEqual(len(data), 1)
		row = frappe._dict(data[0])
		self.assertEqual(row.name, self.item)
		self.compare_analytics_row(row, cols, expected_buckets)

	def generate_stock(self, movement):
		for qty, posting_date in movement:
			args = {"item": self.item, "qty": abs(qty), "posting_date": posting_date}
			args["to_warehouse" if qty > 0 else "from_warehouse"] = self.warehouse
			make_stock_entry(**args)

	def compare_analytics_row(self, report_row, columns, expected_buckets):
		# last (N) cols will be monthly data
		no_of_buckets = len(expected_buckets)
		month_cols = [col["fieldname"] for col in columns[-no_of_buckets:]]

		actual_buckets = [report_row.get(col) for col in month_cols]

		self.assertEqual(actual_buckets, expected_buckets)

	def test_get_period_date_ranges(self):
		filters = _dict(range="Monthly", from_date="2020-12-28", to_date="2021-02-06")

		ranges = get_period_date_ranges(filters)

		expected_ranges = [
			[datetime.date(2020, 12, 1), datetime.date(2020, 12, 31)],
			[datetime.date(2021, 1, 1), datetime.date(2021, 1, 31)],
			[datetime.date(2021, 2, 1), datetime.date(2021, 2, 6)],
		]

		self.assertEqual(ranges, expected_ranges)

	def test_get_period_date_ranges_yearly(self):
		filters = _dict(range="Yearly", from_date="2021-01-28", to_date="2021-02-06")

		ranges = get_period_date_ranges(filters)
		first_date = get_fiscal_year("2021-01-28")[1]
		expected_ranges = [
			[first_date, datetime.date(2021, 2, 6)],
		]

		self.assertEqual(ranges, expected_ranges)

	def test_basic_report_functionality(self):
		"""Stock analytics report generates balance "as of" periods based on
		user defined ranges. Check that this behaviour is correct."""

		# create stock movement in 3 months at 15th of month
		today = getdate()
		movement = [
			(10, add_to_date(today, months=0).replace(day=15)),
			(-5, add_to_date(today, months=1).replace(day=15)),
			(10, add_to_date(today, months=2).replace(day=15)),
		]
		self.assert_single_item_report(movement, [10, 5, 15])

	def test_empty_month_in_between(self):
		today = getdate()
		movement = [
			(100, add_to_date(today, months=0).replace(day=15)),
			(-50, add_to_date(today, months=1).replace(day=15)),
			# Skip a month
			(20, add_to_date(today, months=3).replace(day=15)),
		]
		self.assert_single_item_report(movement, [100, 50, 50, 70])

	def test_multi_month_missings(self):
		today = getdate()
		movement = [
			(100, add_to_date(today, months=0).replace(day=15)),
			(-50, add_to_date(today, months=1).replace(day=15)),
			# Skip a month
			(20, add_to_date(today, months=3).replace(day=15)),
			# Skip another month
			(-10, add_to_date(today, months=5).replace(day=15)),
		]
		self.assert_single_item_report(movement, [100, 50, 50, 70, 70, 60])

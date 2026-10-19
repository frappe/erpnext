import datetime

import frappe
from frappe import _dict
from frappe.utils.data import add_to_date, getdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_analytics.stock_analytics import execute, get_period_date_ranges
from erpnext.tests.utils import ERPNextTestSuite


def stock_analytics(filters):
	col, data, *_ = execute(filters)
	return col, data


class TestStockAnalyticsReport(ERPNextTestSuite):
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

	def test_periods_before_the_first_movement_carry_the_opening_balance(self):
		self.generate_stock([(10, datetime.date(2026, 4, 15)), (5, datetime.date(2026, 8, 10))])
		filters = _dict(
			range="Monthly",
			from_date=datetime.date(2026, 6, 1),
			to_date=datetime.date(2026, 8, 28),
			value_quantity="Quantity",
			company="_Test Company",
			item_code=self.item,
		)

		cols, data = stock_analytics(filters)

		self.compare_analytics_row(frappe._dict(data[0]), cols, [10, 10, 15])

	@ERPNextTestSuite.change_settings("System Settings", {"first_day_of_the_week": "Sunday"})
	def test_weekly_entries_fall_in_the_week_that_contains_them(self):
		self.generate_stock([(3, datetime.date(2026, 8, 16))])
		filters = _dict(
			range="Weekly",
			from_date=datetime.date(2026, 8, 2),
			to_date=datetime.date(2026, 8, 29),
			value_quantity="Quantity",
			company="_Test Company",
			item_code=self.item,
		)

		cols, data = stock_analytics(filters)

		self.compare_analytics_row(frappe._dict(data[0]), cols, [0, 0, 3, 3])

	@ERPNextTestSuite.change_settings("System Settings", {"first_day_of_the_week": "Sunday"})
	def test_weekly_columns_across_a_year_have_unique_labels(self):
		filters = _dict(
			range="Weekly",
			from_date=datetime.date(2022, 1, 1),
			to_date=datetime.date(2022, 12, 31),
			value_quantity="Quantity",
			company="_Test Company",
			item_code=self.item,
		)

		labels = [column["label"] for column in stock_analytics(filters)[0][5:]]

		self.assertEqual(len(labels), len(set(labels)))

	@ERPNextTestSuite.change_settings("System Settings", {"first_day_of_the_week": "Sunday"})
	def test_weeks_across_the_new_year_keep_their_own_balance(self):
		self.generate_stock([(3, datetime.date(2023, 1, 1))])
		filters = _dict(
			range="Weekly",
			from_date=datetime.date(2022, 12, 25),
			to_date=datetime.date(2023, 1, 1),
			value_quantity="Quantity",
			company="_Test Company",
			item_code=self.item,
		)

		cols, data = stock_analytics(filters)

		self.compare_analytics_row(frappe._dict(data[0]), cols, [0, 3])

	def get_quantity_for_restricted_user(self, applicable_for=None):
		from frappe.permissions import add_user_permission

		make_stock_entry(
			item=self.item, to_warehouse="Stores - _TC", qty=10, posting_date=datetime.date(2026, 8, 5)
		)
		make_stock_entry(
			item=self.item, to_warehouse="Finished Goods - _TC", qty=2, posting_date=datetime.date(2026, 8, 5)
		)
		user = "stock-analytics-warehouse@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Analytics", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Stock User")
		add_user_permission("Warehouse", "Finished Goods - _TC", user, applicable_for=applicable_for)

		filters = _dict(
			range="Monthly",
			from_date=datetime.date(2026, 8, 1),
			to_date=datetime.date(2026, 8, 28),
			value_quantity="Quantity",
			company="_Test Company",
			item_code=self.item,
		)
		frappe.set_user(user)
		try:
			cols, data = stock_analytics(filters)
		finally:
			frappe.set_user("Administrator")

		return cols, frappe._dict(data[0])

	def test_rows_count_only_permitted_warehouses(self):
		cols, row = self.get_quantity_for_restricted_user()
		self.compare_analytics_row(row, cols, [2])

	def test_permission_for_another_doctype_does_not_limit_rows(self):
		cols, row = self.get_quantity_for_restricted_user(applicable_for="Purchase Order")
		self.compare_analytics_row(row, cols, [12])

	def test_period_ranges_reach_the_to_date(self):
		filters = _dict(range="Weekly", from_date="2026-03-30", to_date="2027-03-31")

		ranges = get_period_date_ranges(filters)

		self.assertEqual(getdate(ranges[-1][1]), getdate("2027-03-31"))

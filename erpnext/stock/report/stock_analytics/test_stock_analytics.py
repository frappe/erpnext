import datetime

from frappe import _dict
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.report.stock_analytics.stock_analytics import get_period_date_ranges


class TestStockAnalyticsReport(FrappeTestCase):
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

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest
from contextlib import contextmanager
from datetime import date, timedelta

import frappe
from frappe.utils import getdate

from erpnext.setup.doctype.holiday_list.holiday_list import local_country_name


class TestHolidayList(unittest.TestCase):
	def test_holiday_list(self):
		today_date = getdate()
		test_holiday_dates = [today_date - timedelta(days=5), today_date - timedelta(days=4)]
		holiday_list = make_holiday_list(
			"test_holiday_list",
			holiday_dates=[
				{"holiday_date": test_holiday_dates[0], "description": "test holiday"},
				{"holiday_date": test_holiday_dates[1], "description": "test holiday2"},
			],
		)
		fetched_holiday_list = frappe.get_value("Holiday List", holiday_list.name)
		self.assertEqual(holiday_list.name, fetched_holiday_list)

	def test_weekly_off(self):
		holiday_list = frappe.new_doc("Holiday List")
		holiday_list.from_date = "2023-01-01"
		holiday_list.to_date = "2023-02-28"
		holiday_list.weekly_off = "Sunday"
		holiday_list.get_weekly_off_dates()

		holidays = [holiday.holiday_date for holiday in holiday_list.holidays]

		self.assertNotIn(date(2022, 12, 25), holidays)
		self.assertIn(date(2023, 1, 1), holidays)
		self.assertIn(date(2023, 1, 8), holidays)
		self.assertIn(date(2023, 1, 15), holidays)
		self.assertIn(date(2023, 1, 22), holidays)
		self.assertIn(date(2023, 1, 29), holidays)
		self.assertIn(date(2023, 2, 5), holidays)
		self.assertIn(date(2023, 2, 12), holidays)
		self.assertIn(date(2023, 2, 19), holidays)
		self.assertIn(date(2023, 2, 26), holidays)
		self.assertNotIn(date(2023, 3, 5), holidays)

	def test_local_holidays(self):
		holiday_list = frappe.new_doc("Holiday List")
		holiday_list.from_date = "2023-04-01"
		holiday_list.to_date = "2023-04-30"
		holiday_list.country = "DE"
		holiday_list.subdivision = "SN"
		holiday_list.get_local_holidays()

		holidays = [holiday.holiday_date for holiday in holiday_list.holidays]
		self.assertNotIn(date(2023, 1, 1), holidays)
		self.assertIn(date(2023, 4, 7), holidays)
		self.assertIn(date(2023, 4, 10), holidays)
		self.assertNotIn(date(2023, 5, 1), holidays)

	def test_localized_country_names(self):
		lang = frappe.local.lang
		frappe.local.lang = "en-gb"
		self.assertEqual(local_country_name("IN"), "India")
		self.assertEqual(local_country_name("DE"), "Germany")

		frappe.local.lang = "de"
		self.assertEqual(local_country_name("DE"), "Deutschland")
		frappe.local.lang = lang


def make_holiday_list(
	name, from_date=getdate() - timedelta(days=10), to_date=getdate(), holiday_dates=None
):
	frappe.delete_doc_if_exists("Holiday List", name, force=1)
	doc = frappe.get_doc(
		{
			"doctype": "Holiday List",
			"holiday_list_name": name,
			"from_date": from_date,
			"to_date": to_date,
			"holidays": holiday_dates,
		}
	).insert()
	return doc


@contextmanager
def set_holiday_list(holiday_list, company_name):
	"""
	Context manager for setting holiday list in tests
	"""
	try:
		company = frappe.get_doc("Company", company_name)
		previous_holiday_list = company.default_holiday_list

		company.default_holiday_list = holiday_list
		company.save()

		yield

	finally:
		# restore holiday list setup
		company = frappe.get_doc("Company", company_name)
		company.default_holiday_list = previous_holiday_list
		company.save()

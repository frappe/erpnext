# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest
from contextlib import contextmanager
from datetime import timedelta

import frappe
from frappe.utils import getdate


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

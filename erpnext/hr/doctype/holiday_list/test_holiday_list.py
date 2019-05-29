# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import getdate
from datetime import timedelta
from erpnext.hr.doctype.employee.test_employee import make_employee


class TestHolidayList(unittest.TestCase):
	def test_get_holiday_list(self):
		holiday_list = make_holiday_list("test_get_holiday_list")
		employee = make_employee("test_get_holiday_list@example.com")
		employee = frappe.get_doc("Employee", employee)
		employee.holiday_list = None
		employee.save()
		company = frappe.get_doc("Company", employee.company)
		company_default_holiday_list = company.default_holiday_list

		from erpnext.hr.doctype.holiday_list.holiday_list import get_holiday_list
		holiday_list_name = get_holiday_list(employee.name)
		self.assertEqual(holiday_list_name, company_default_holiday_list)

		employee.holiday_list = holiday_list.name
		employee.save()
		holiday_list_name = get_holiday_list(employee.name)
		self.assertEqual(holiday_list_name, holiday_list.name)


def make_holiday_list(name, from_date=getdate()-timedelta(days=10), to_date=getdate(), holiday_dates=None):
	if not frappe.db.get_value("Holiday List", name):
		doc = frappe.get_doc({
			"doctype": "Holiday List",
			"holiday_list_name": name,
			"from_date" : from_date,
			"to_date" : to_date
			}).insert()
		doc.holidays = holiday_dates
		doc.save()
	else:
		doc = frappe.get_doc("Holiday List", name)
	return doc

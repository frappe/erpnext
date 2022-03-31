# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import getdate

import erpnext
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.upload_attendance.upload_attendance import get_data

test_dependencies = ["Holiday List"]


class TestUploadAttendance(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		frappe.db.set_value(
			"Company", erpnext.get_default_company(), "default_holiday_list", "_Test Holiday List"
		)

	def test_date_range(self):
		employee = make_employee("test_employee@company.com")
		employee_doc = frappe.get_doc("Employee", employee)
		date_of_joining = "2018-01-02"
		relieving_date = "2018-01-03"
		from_date = "2018-01-01"
		to_date = "2018-01-04"
		employee_doc.date_of_joining = date_of_joining
		employee_doc.relieving_date = relieving_date
		employee_doc.save()
		args = {"from_date": from_date, "to_date": to_date}
		data = get_data(args)
		filtered_data = []
		for row in data:
			if row[1] == employee:
				filtered_data.append(row)
		for row in filtered_data:
			self.assertTrue(
				getdate(row[3]) >= getdate(date_of_joining) and getdate(row[3]) <= getdate(relieving_date)
			)

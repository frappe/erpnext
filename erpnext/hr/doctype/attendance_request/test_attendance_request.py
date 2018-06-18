# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import add_days, nowdate
from datetime import date

class TestAttendanceRequest(unittest.TestCase):
	def setUp(self):
		for dt in ["Attendance Request", "Attendance"]:
			frappe.db.sql("delete from `tab%s`" % dt)

	def test_attendance_request(self):
		today = nowdate()
		employee = get_employee()
		attendance_request = frappe.new_doc("Attendance Request")
		attendance_request.employee = employee.name
		attendance_request.from_date = date(date.today().year, 1, 1)
		attendance_request.to_date = date(date.today().year, 1, 2)
		attendance_request.reason = "Work From Home"
		attendance_request.company = "_Test Company"
		attendance_request.insert()
		attendance_request.submit()
		attendance = frappe.get_doc('Attendance', {
			'employee': employee.name,
			'attendance_date': date(date.today().year, 1, 1)
		})
		self.assertEqual(attendance.status, 'Present')

def get_employee():
	return frappe.get_doc("Employee", "_T-Employee-00001")
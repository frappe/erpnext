# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.hr.utils import create_standard_attendance_status

class TestAttendanceStatus(unittest.TestCase):
	def setUp(self):
		create_standard_attendance_status()

	def test_attendance_status_can_be_either_present_leave_or_half_day(self):
		att_status = create_attendace_status("Test Status", "T", is_present=1, is_half_day=1, is_leave=1)
		self.assertRaises(frappe.ValidationError, att_status.save)

	def test_duplicate_attendance_status_is_present_with_same_default_property(self):

		att_status = create_attendace_status("Present Status 2", "T", is_present=1, applicable_for_employee_checkins=1)
		self.assertRaises(frappe.ValidationError, att_status.save)

	def test_duplicate_attendance_status_is_half_day_with_same_default_property(self):

		att_status_3 = create_attendace_status("Half day Status 3", "T", is_half_day=1, applicable_for_employee_checkins=1)
		self.assertRaises(frappe.ValidationError, att_status_3.save)


		att_status_5 = create_attendace_status("Half day Status 5", "T", is_half_day=1, applicable_for_leave_application=1)
		self.assertRaises(frappe.ValidationError, att_status_5.save)

		att_status_4 = create_attendace_status("Half day Status 4", "T", is_half_day=1, applicable_for_attendance_request=1)
		self.assertRaises(frappe.ValidationError, att_status_4.save)

	def test_duplicate_attendance_status_is_leave_with_same_default_property(self):

		att_status_2 = create_attendace_status("On Leave Status 2", "T", is_leave=1, applicable_for_leave_application=1)

		self.assertRaises(frappe.ValidationError, att_status_2.save)

	def tearDown(self):
		frappe.db.sql("""DELETE FROM `tabAttendance Status` WHERE name not in ('Present', 'Absent', 'On Leave', 'Work From Home', 'Half Day')""")


def create_attendace_status(name, abbr, **args):
	args = frappe._dict(args)

	attendacne_status = frappe.new_doc("Attendance Status")
	attendacne_status.name = name
	attendacne_status.abbr = abbr
	attendacne_status.is_present = args.is_present or 0
	attendacne_status.is_half_day = args.is_half_day or 0
	attendacne_status.is_leave = args.is_leave or 0
	attendacne_status.applicable_for_leave_application = args.applicable_for_leave_application or 0
	attendacne_status.applicable_for_employee_checkins = args.applicable_for_employee_checkins or 0
	attendacne_status.applicable_for_attendance_request = args.applicable_for_attendance_request or 0

	return attendacne_status

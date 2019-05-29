# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.hr.doctype.employee.test_employee import make_employee
from frappe.utils import now_datetime
from datetime import timedelta

class TestHRSettings(unittest.TestCase):
	def test_get_employee_attendance_log_last_sync(self):
		doc = frappe.get_doc("HR Settings")
		doc.last_sync_of_attendance_log = None
		doc.save()
		hr_settings = frappe.db.get_singles_dict("HR Settings")
		doc.last_sync_of_attendance_log = now_datetime()
		doc.save()

		from erpnext.hr.doctype.hr_settings.hr_settings import get_employee_attendance_log_last_sync
		employee = make_employee("test_attendance_log_last_sync@example.com")

		frappe.db.delete('Employee Attendance Log',{'employee':'EMP-00001'})
		employee_last_sync = get_employee_attendance_log_last_sync(employee, hr_settings)
		self.assertEqual(employee_last_sync, None)

		employee_last_sync = get_employee_attendance_log_last_sync(employee)
		self.assertEqual(employee_last_sync, doc.last_sync_of_attendance_log)

		from erpnext.hr.doctype.employee_attendance_log.test_employee_attendance_log import make_attendance_log
		time_now = now_datetime()
		make_attendance_log(employee, time_now)
		employee_last_sync = get_employee_attendance_log_last_sync(employee)
		self.assertEqual(employee_last_sync, time_now)

	def test_calculate_working_hours(self):
		check_in_out_type = ['Alternating entries as IN and OUT during the same shift',
			'Strictly based on Log Type in Employee Attendance Log'] 
		working_hours_calc_type = ['First Check-in and Last Check-out',
			'Every Valid Check-in and Check-out']
		logs_type_1 = [
			{'time':now_datetime()-timedelta(minutes=390)},
			{'time':now_datetime()-timedelta(minutes=300)},
			{'time':now_datetime()-timedelta(minutes=270)},
			{'time':now_datetime()-timedelta(minutes=90)},
			{'time':now_datetime()-timedelta(minutes=0)}
			]
		logs_type_2 = [
			{'time':now_datetime()-timedelta(minutes=390),'log_type':'OUT'},
			{'time':now_datetime()-timedelta(minutes=360),'log_type':'IN'},
			{'time':now_datetime()-timedelta(minutes=300),'log_type':'OUT'},
			{'time':now_datetime()-timedelta(minutes=290),'log_type':'IN'},
			{'time':now_datetime()-timedelta(minutes=260),'log_type':'OUT'},
			{'time':now_datetime()-timedelta(minutes=240),'log_type':'IN'},
			{'time':now_datetime()-timedelta(minutes=150),'log_type':'IN'},
			{'time':now_datetime()-timedelta(minutes=60),'log_type':'OUT'}
			]
		logs_type_1 = [frappe._dict(x) for x in logs_type_1]
		logs_type_2 = [frappe._dict(x) for x in logs_type_2]

		from erpnext.hr.doctype.hr_settings.hr_settings import calculate_working_hours

		working_hours = calculate_working_hours(logs_type_1,check_in_out_type[0],working_hours_calc_type[0])
		self.assertEqual(working_hours, 6.5)

		working_hours = calculate_working_hours(logs_type_1,check_in_out_type[0],working_hours_calc_type[1])
		self.assertEqual(working_hours, 4.5)

		working_hours = calculate_working_hours(logs_type_2,check_in_out_type[1],working_hours_calc_type[0])
		self.assertEqual(working_hours, 5)

		working_hours = calculate_working_hours(logs_type_2,check_in_out_type[1],working_hours_calc_type[1])
		self.assertEqual(working_hours, 4.5)




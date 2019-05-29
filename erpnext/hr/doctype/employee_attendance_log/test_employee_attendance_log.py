# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import now_datetime, nowdate, to_timedelta
import unittest
from datetime import timedelta

from erpnext.hr.doctype.employee_attendance_log.employee_attendance_log import add_log_based_on_biometric_rf_id, mark_attendance_and_link_log
from erpnext.hr.doctype.employee.test_employee import make_employee

class TestEmployeeAttendanceLog(unittest.TestCase):
	def test_add_log_based_on_biometric_rf_id(self):
		employee = make_employee("test_add_log_based_on_biometric_rf_id@example.com")
		employee = frappe.get_doc("Employee", employee)
		employee.biometric_rf_id = '3344'
		employee.save()

		time_now = now_datetime().__str__()[:-7]
		employee_attendance_log = add_log_based_on_biometric_rf_id('3344', time_now, 'mumbai_first_floor', 'IN')
		self.assertEqual(employee_attendance_log.employee, employee.name)
		self.assertEqual(employee_attendance_log.time, time_now)
		self.assertEqual(employee_attendance_log.device_id, 'mumbai_first_floor')
		self.assertEqual(employee_attendance_log.log_type, 'IN')

	def test_mark_attendance_and_link_log(self):
		employee = make_employee("test_mark_attendance_and_link_log@example.com")
		logs = make_n_attendance_logs(employee, 3)
		mark_attendance_and_link_log(logs, 'Skip', nowdate())
		log_names = [log.name for log in logs]
		logs_count = frappe.db.count('Employee Attendance Log', {'name':['in', log_names], 'skip_auto_attendance':1})
		self.assertEqual(logs_count, 3)

		logs = make_n_attendance_logs(employee, 4, 2)
		now_date = nowdate()
		frappe.db.delete('Attendance', {'employee':employee})
		attendance = mark_attendance_and_link_log(logs, 'Present', now_date, 8.2)
		log_names = [log.name for log in logs]
		logs_count = frappe.db.count('Employee Attendance Log', {'name':['in', log_names], 'attendance':attendance.name})
		self.assertEqual(logs_count, 4)
		attendance_count = frappe.db.count('Attendance', {'status':'Present', 'working_hours':8.2,
			'employee':employee, 'attendance_date':now_date})
		self.assertEqual(attendance_count, 1)		


def make_n_attendance_logs(employee, n, hours_to_reverse=1):
	logs = [make_attendance_log(employee, now_datetime() - timedelta(hours=hours_to_reverse, minutes=n+1))]
	for i in range(n-1):
		logs.append(make_attendance_log(employee, now_datetime() - timedelta(hours=hours_to_reverse, minutes=n-i)))
	return logs


def make_attendance_log(employee, time=now_datetime()):
	log = frappe.get_doc({
		"doctype": "Employee Attendance Log",
		"employee" : employee,
		"time" : time,
		"device_id" : "device1",
		"log_type" : "IN"
		}).insert()
	return log
# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from datetime import timedelta

import frappe
from frappe.utils import now_datetime, nowdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.employee_checkin.employee_checkin import (
	add_log_based_on_employee_field,
	calculate_working_hours,
	mark_attendance_and_link_log,
)


class TestEmployeeCheckin(unittest.TestCase):
	def test_add_log_based_on_employee_field(self):
		employee = make_employee("test_add_log_based_on_employee_field@example.com")
		employee = frappe.get_doc("Employee", employee)
		employee.attendance_device_id = '3344'
		employee.save()

		time_now = now_datetime().__str__()[:-7]
		employee_checkin = add_log_based_on_employee_field('3344', time_now, 'mumbai_first_floor', 'IN')
		self.assertEqual(employee_checkin.employee, employee.name)
		self.assertEqual(employee_checkin.time, time_now)
		self.assertEqual(employee_checkin.device_id, 'mumbai_first_floor')
		self.assertEqual(employee_checkin.log_type, 'IN')

	def test_mark_attendance_and_link_log(self):
		employee = make_employee("test_mark_attendance_and_link_log@example.com")
		logs = make_n_checkins(employee, 3)
		mark_attendance_and_link_log(logs, 'Skip', nowdate())
		log_names = [log.name for log in logs]
		logs_count = frappe.db.count('Employee Checkin', {'name':['in', log_names], 'skip_auto_attendance':1})
		self.assertEqual(logs_count, 3)

		logs = make_n_checkins(employee, 4, 2)
		now_date = nowdate()
		frappe.db.delete('Attendance', {'employee':employee})
		attendance = mark_attendance_and_link_log(logs, 'Present', now_date, 8.2)
		log_names = [log.name for log in logs]
		logs_count = frappe.db.count('Employee Checkin', {'name':['in', log_names], 'attendance':attendance.name})
		self.assertEqual(logs_count, 4)
		attendance_count = frappe.db.count('Attendance', {'status':'Present', 'working_hours':8.2,
			'employee':employee, 'attendance_date':now_date})
		self.assertEqual(attendance_count, 1)

	def test_calculate_working_hours(self):
		check_in_out_type = ['Alternating entries as IN and OUT during the same shift',
			'Strictly based on Log Type in Employee Checkin']
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

		working_hours = calculate_working_hours(logs_type_1,check_in_out_type[0],working_hours_calc_type[0])
		self.assertEqual(working_hours, (6.5, logs_type_1[0].time, logs_type_1[-1].time))

		working_hours = calculate_working_hours(logs_type_1,check_in_out_type[0],working_hours_calc_type[1])
		self.assertEqual(working_hours, (4.5, logs_type_1[0].time, logs_type_1[-1].time))

		working_hours = calculate_working_hours(logs_type_2,check_in_out_type[1],working_hours_calc_type[0])
		self.assertEqual(working_hours, (5, logs_type_2[1].time, logs_type_2[-1].time))

		working_hours = calculate_working_hours(logs_type_2,check_in_out_type[1],working_hours_calc_type[1])
		self.assertEqual(working_hours, (4.5, logs_type_2[1].time, logs_type_2[-1].time))

def make_n_checkins(employee, n, hours_to_reverse=1):
	logs = [make_checkin(employee, now_datetime() - timedelta(hours=hours_to_reverse, minutes=n+1))]
	for i in range(n-1):
		logs.append(make_checkin(employee, now_datetime() - timedelta(hours=hours_to_reverse, minutes=n-i)))
	return logs


def make_checkin(employee, time=now_datetime()):
	log = frappe.get_doc({
		"doctype": "Employee Checkin",
		"employee" : employee,
		"time" : time,
		"device_id" : "device1",
		"log_type" : "IN"
		}).insert()
	return log

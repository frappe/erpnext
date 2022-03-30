# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from datetime import datetime, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_time, getdate, now_datetime, nowdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.employee_checkin.employee_checkin import (
	add_log_based_on_employee_field,
	calculate_working_hours,
	mark_attendance_and_link_log,
)
from erpnext.hr.doctype.leave_application.test_leave_application import get_first_sunday


class TestEmployeeCheckin(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Shift Type")
		frappe.db.delete("Shift Assignment")
		frappe.db.delete("Employee Checkin")

	def test_add_log_based_on_employee_field(self):
		employee = make_employee("test_add_log_based_on_employee_field@example.com")
		employee = frappe.get_doc("Employee", employee)
		employee.attendance_device_id = "3344"
		employee.save()

		time_now = now_datetime().__str__()[:-7]
		employee_checkin = add_log_based_on_employee_field("3344", time_now, "mumbai_first_floor", "IN")
		self.assertEqual(employee_checkin.employee, employee.name)
		self.assertEqual(employee_checkin.time, time_now)
		self.assertEqual(employee_checkin.device_id, "mumbai_first_floor")
		self.assertEqual(employee_checkin.log_type, "IN")

	def test_mark_attendance_and_link_log(self):
		employee = make_employee("test_mark_attendance_and_link_log@example.com")
		logs = make_n_checkins(employee, 3)
		mark_attendance_and_link_log(logs, "Skip", nowdate())
		log_names = [log.name for log in logs]
		logs_count = frappe.db.count(
			"Employee Checkin", {"name": ["in", log_names], "skip_auto_attendance": 1}
		)
		self.assertEqual(logs_count, 3)

		logs = make_n_checkins(employee, 4, 2)
		now_date = nowdate()
		frappe.db.delete("Attendance", {"employee": employee})
		attendance = mark_attendance_and_link_log(logs, "Present", now_date, 8.2)
		log_names = [log.name for log in logs]
		logs_count = frappe.db.count(
			"Employee Checkin", {"name": ["in", log_names], "attendance": attendance.name}
		)
		self.assertEqual(logs_count, 4)
		attendance_count = frappe.db.count(
			"Attendance",
			{"status": "Present", "working_hours": 8.2, "employee": employee, "attendance_date": now_date},
		)
		self.assertEqual(attendance_count, 1)

	def test_calculate_working_hours(self):
		check_in_out_type = [
			"Alternating entries as IN and OUT during the same shift",
			"Strictly based on Log Type in Employee Checkin",
		]
		working_hours_calc_type = [
			"First Check-in and Last Check-out",
			"Every Valid Check-in and Check-out",
		]
		logs_type_1 = [
			{"time": now_datetime() - timedelta(minutes=390)},
			{"time": now_datetime() - timedelta(minutes=300)},
			{"time": now_datetime() - timedelta(minutes=270)},
			{"time": now_datetime() - timedelta(minutes=90)},
			{"time": now_datetime() - timedelta(minutes=0)},
		]
		logs_type_2 = [
			{"time": now_datetime() - timedelta(minutes=390), "log_type": "OUT"},
			{"time": now_datetime() - timedelta(minutes=360), "log_type": "IN"},
			{"time": now_datetime() - timedelta(minutes=300), "log_type": "OUT"},
			{"time": now_datetime() - timedelta(minutes=290), "log_type": "IN"},
			{"time": now_datetime() - timedelta(minutes=260), "log_type": "OUT"},
			{"time": now_datetime() - timedelta(minutes=240), "log_type": "IN"},
			{"time": now_datetime() - timedelta(minutes=150), "log_type": "IN"},
			{"time": now_datetime() - timedelta(minutes=60), "log_type": "OUT"},
		]
		logs_type_1 = [frappe._dict(x) for x in logs_type_1]
		logs_type_2 = [frappe._dict(x) for x in logs_type_2]

		working_hours = calculate_working_hours(
			logs_type_1, check_in_out_type[0], working_hours_calc_type[0]
		)
		self.assertEqual(working_hours, (6.5, logs_type_1[0].time, logs_type_1[-1].time))

		working_hours = calculate_working_hours(
			logs_type_1, check_in_out_type[0], working_hours_calc_type[1]
		)
		self.assertEqual(working_hours, (4.5, logs_type_1[0].time, logs_type_1[-1].time))

		working_hours = calculate_working_hours(
			logs_type_2, check_in_out_type[1], working_hours_calc_type[0]
		)
		self.assertEqual(working_hours, (5, logs_type_2[1].time, logs_type_2[-1].time))

		working_hours = calculate_working_hours(
			logs_type_2, check_in_out_type[1], working_hours_calc_type[1]
		)
		self.assertEqual(working_hours, (4.5, logs_type_2[1].time, logs_type_2[-1].time))

	def test_fetch_shift(self):
		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")

		# shift setup for 8-12
		shift_type = setup_shift_type()
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		# within shift time
		timestamp = datetime.combine(date, get_time("08:45:00"))
		log = make_checkin(employee, timestamp)
		self.assertEqual(log.shift, shift_type.name)

		# "begin checkin before shift time" = 60 mins, so should work for 7:00:00
		timestamp = datetime.combine(date, get_time("07:00:00"))
		log = make_checkin(employee, timestamp)
		self.assertEqual(log.shift, shift_type.name)

		# "allow checkout after shift end time" = 60 mins, so should work for 13:00:00
		timestamp = datetime.combine(date, get_time("13:00:00"))
		log = make_checkin(employee, timestamp)
		self.assertEqual(log.shift, shift_type.name)

		# should not fetch this shift beyond allowed time
		timestamp = datetime.combine(date, get_time("13:01:00"))
		log = make_checkin(employee, timestamp)
		self.assertIsNone(log.shift)

	def test_shift_start_and_end_timings(self):
		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")

		# shift setup for 8-12
		shift_type = setup_shift_type()
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		timestamp = datetime.combine(date, get_time("08:45:00"))
		log = make_checkin(employee, timestamp)

		self.assertEqual(log.shift, shift_type.name)
		self.assertEqual(log.shift_start, datetime.combine(date, get_time("08:00:00")))
		self.assertEqual(log.shift_end, datetime.combine(date, get_time("12:00:00")))
		self.assertEqual(log.shift_actual_start, datetime.combine(date, get_time("07:00:00")))
		self.assertEqual(log.shift_actual_end, datetime.combine(date, get_time("13:00:00")))

	def test_fetch_shift_based_on_default_shift(self):
		employee = make_employee("test_default_shift@example.com", company="_Test Company")
		default_shift = setup_shift_type(
			shift_type="Default Shift", start_time="14:00:00", end_time="16:00:00"
		)

		date = getdate()
		frappe.db.set_value("Employee", employee, "default_shift", default_shift.name)

		timestamp = datetime.combine(date, get_time("14:45:00"))
		log = make_checkin(employee, timestamp)

		# should consider default shift
		self.assertEqual(log.shift, default_shift.name)

	def test_fetch_shift_spanning_over_two_days(self):
		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")
		shift_type = setup_shift_type(start_time="23:00:00", end_time="01:00:00")
		date = getdate()
		next_day = add_days(date, 1)
		make_shift_assignment(shift_type.name, employee, date)

		# log falls in the first day
		timestamp = datetime.combine(date, get_time("23:00:00"))
		log = make_checkin(employee, timestamp)

		self.assertEqual(log.shift, shift_type.name)
		self.assertEqual(log.shift_start, datetime.combine(date, get_time("23:00:00")))
		self.assertEqual(log.shift_end, datetime.combine(next_day, get_time("01:00:00")))
		self.assertEqual(log.shift_actual_start, datetime.combine(date, get_time("22:00:00")))
		self.assertEqual(log.shift_actual_end, datetime.combine(next_day, get_time("02:00:00")))

		log.delete()

		# log falls in the second day
		prev_day = add_days(date, -1)
		timestamp = datetime.combine(date, get_time("01:30:00"))
		log = make_checkin(employee, timestamp)
		self.assertEqual(log.shift, shift_type.name)
		self.assertEqual(log.shift_start, datetime.combine(prev_day, get_time("23:00:00")))
		self.assertEqual(log.shift_end, datetime.combine(date, get_time("01:00:00")))
		self.assertEqual(log.shift_actual_start, datetime.combine(prev_day, get_time("22:00:00")))
		self.assertEqual(log.shift_actual_end, datetime.combine(date, get_time("02:00:00")))

	def test_no_shift_fetched_on_a_holiday(self):
		employee = make_employee("test_shift_with_holiday@example.com", company="_Test Company")
		setup_shift_type(
			shift_type="Test Holiday Shift", holiday_list="Salary Slip Test Holiday List"
		)
		date = getdate()

		first_sunday = get_first_sunday("Salary Slip Test Holiday List", for_date=date)
		timestamp = datetime.combine(first_sunday, get_time("08:00:00"))
		log = make_checkin(employee, timestamp)

		self.assertIsNone(log.shift)

	def test_consecutive_shift_assignments_overlapping_within_grace_period(self):
		# test adjustment for start and end times if they are overlapping
		# within "begin_check_in_before_shift_start_time" and "allow_check_out_after_shift_end_time" periods
		employee = make_employee("test_shift_with_holiday@example.com", company="_Test Company")

		# 8 - 12
		shift1 = setup_shift_type()
		# 12:30 - 16:30
		shift2 = setup_shift_type(
			shift_type="Consecutive Shift", start_time="12:30:00", end_time="16:30:00"
		)

		# the actual start and end times (with grace) for these shifts are 7 - 13 and 11:30 - 17:30
		date = getdate()
		make_shift_assignment(shift1.name, employee, date)
		make_shift_assignment(shift2.name, employee, date)

		# log at 12:30 should set shift2 and actual start as 12 and not 11:30
		timestamp = datetime.combine(date, get_time("12:30:00"))
		log = make_checkin(employee, timestamp)
		self.assertEqual(log.shift, shift2.name)
		self.assertEqual(log.shift_start, datetime.combine(date, get_time("12:30:00")))
		self.assertEqual(log.shift_actual_start, datetime.combine(date, get_time("12:00:00")))

		# log at 12:00 should set shift1 and actual end as 12 and not 1 since the next shift's grace starts
		timestamp = datetime.combine(date, get_time("12:00:00"))
		log = make_checkin(employee, timestamp)
		self.assertEqual(log.shift, shift1.name)
		self.assertEqual(log.shift_end, datetime.combine(date, get_time("12:00:00")))
		self.assertEqual(log.shift_actual_end, datetime.combine(date, get_time("12:00:00")))

		# log at 12:01 should set shift2
		timestamp = datetime.combine(date, get_time("12:01:00"))
		log = make_checkin(employee, timestamp)
		self.assertEqual(log.shift, shift2.name)


def make_n_checkins(employee, n, hours_to_reverse=1):
	logs = [make_checkin(employee, now_datetime() - timedelta(hours=hours_to_reverse, minutes=n + 1))]
	for i in range(n - 1):
		logs.append(
			make_checkin(employee, now_datetime() - timedelta(hours=hours_to_reverse, minutes=n - i))
		)
	return logs


def make_checkin(employee, time=now_datetime()):
	log = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"time": time,
			"device_id": "device1",
			"log_type": "IN",
		}
	).insert()
	return log


def setup_shift_type(**args):
	args = frappe._dict(args)
	shift_type = frappe.new_doc("Shift Type")
	shift_type.__newname = args.shift_type or "_Test Shift"
	shift_type.start_time = args.start_time or "08:00:00"
	shift_type.end_time = args.end_time or "12:00:00"
	shift_type.holiday_list = args.holiday_list
	shift_type.enable_auto_attendance = 1

	shift_type.determine_check_in_and_check_out = (
		args.determine_check_in_and_check_out
		or "Alternating entries as IN and OUT during the same shift"
	)
	shift_type.working_hours_calculation_based_on = (
		args.working_hours_calculation_based_on or "First Check-in and Last Check-out"
	)
	shift_type.begin_check_in_before_shift_start_time = (
		args.begin_check_in_before_shift_start_time or 60
	)
	shift_type.allow_check_out_after_shift_end_time = args.allow_check_out_after_shift_end_time or 60

	shift_type.save()

	return shift_type


def make_shift_assignment(shift_type, employee, start_date, end_date=None):
	shift_assignment = frappe.get_doc(
		{
			"doctype": "Shift Assignment",
			"shift_type": shift_type,
			"company": "_Test Company",
			"employee": employee,
			"start_date": start_date,
			"end_date": end_date,
		}
	).insert()
	shift_assignment.submit()

	return shift_assignment

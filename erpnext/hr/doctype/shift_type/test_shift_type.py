# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from datetime import datetime, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_time, get_year_ending, get_year_start, getdate, now_datetime

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.holiday_list.test_holiday_list import set_holiday_list
from erpnext.hr.doctype.leave_application.test_leave_application import get_first_sunday
from erpnext.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list


class TestShiftType(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Shift Type")
		frappe.db.delete("Shift Assignment")
		frappe.db.delete("Employee Checkin")
		frappe.db.delete("Attendance")

		from_date = get_year_start(getdate())
		to_date = get_year_ending(getdate())
		self.holiday_list = make_holiday_list(from_date=from_date, to_date=to_date)

	def test_mark_attendance(self):
		from erpnext.hr.doctype.employee_checkin.test_employee_checkin import make_checkin

		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")

		shift_type = setup_shift_type()
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		timestamp = datetime.combine(date, get_time("08:00:00"))
		log_in = make_checkin(employee, timestamp)
		self.assertEqual(log_in.shift, shift_type.name)

		timestamp = datetime.combine(date, get_time("12:00:00"))
		log_out = make_checkin(employee, timestamp)
		self.assertEqual(log_out.shift, shift_type.name)

		shift_type.process_auto_attendance()

		attendance = frappe.db.get_value(
			"Attendance", {"shift": shift_type.name}, ["status", "name"], as_dict=True
		)
		self.assertEqual(attendance.status, "Present")

	def test_entry_and_exit_grace(self):
		from erpnext.hr.doctype.employee_checkin.test_employee_checkin import make_checkin

		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")

		# doesn't mark late entry until 60 mins after shift start i.e. till 9
		# doesn't mark late entry until 60 mins before shift end i.e. 11
		shift_type = setup_shift_type(
			enable_entry_grace_period=1,
			enable_exit_grace_period=1,
			late_entry_grace_period=60,
			early_exit_grace_period=60,
		)
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		timestamp = datetime.combine(date, get_time("09:30:00"))
		log_in = make_checkin(employee, timestamp)
		self.assertEqual(log_in.shift, shift_type.name)

		timestamp = datetime.combine(date, get_time("10:30:00"))
		log_out = make_checkin(employee, timestamp)
		self.assertEqual(log_out.shift, shift_type.name)

		shift_type.process_auto_attendance()

		attendance = frappe.db.get_value(
			"Attendance",
			{"shift": shift_type.name},
			["status", "name", "late_entry", "early_exit"],
			as_dict=True,
		)
		self.assertEqual(attendance.status, "Present")
		self.assertEqual(attendance.late_entry, 1)
		self.assertEqual(attendance.early_exit, 1)

	def test_working_hours_threshold_for_half_day(self):
		from erpnext.hr.doctype.employee_checkin.test_employee_checkin import make_checkin

		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")
		shift_type = setup_shift_type(shift_type="Half Day Test", working_hours_threshold_for_half_day=2)
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		timestamp = datetime.combine(date, get_time("08:00:00"))
		log_in = make_checkin(employee, timestamp)
		self.assertEqual(log_in.shift, shift_type.name)

		timestamp = datetime.combine(date, get_time("09:30:00"))
		log_out = make_checkin(employee, timestamp)
		self.assertEqual(log_out.shift, shift_type.name)

		shift_type.process_auto_attendance()

		attendance = frappe.db.get_value(
			"Attendance", {"shift": shift_type.name}, ["status", "working_hours"], as_dict=True
		)
		self.assertEqual(attendance.status, "Half Day")
		self.assertEqual(attendance.working_hours, 1.5)

	def test_working_hours_threshold_for_absent(self):
		from erpnext.hr.doctype.employee_checkin.test_employee_checkin import make_checkin

		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")
		shift_type = setup_shift_type(shift_type="Absent Test", working_hours_threshold_for_absent=2)
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		timestamp = datetime.combine(date, get_time("08:00:00"))
		log_in = make_checkin(employee, timestamp)
		self.assertEqual(log_in.shift, shift_type.name)

		timestamp = datetime.combine(date, get_time("09:30:00"))
		log_out = make_checkin(employee, timestamp)
		self.assertEqual(log_out.shift, shift_type.name)

		shift_type.process_auto_attendance()

		attendance = frappe.db.get_value(
			"Attendance", {"shift": shift_type.name}, ["status", "working_hours"], as_dict=True
		)
		self.assertEqual(attendance.status, "Absent")
		self.assertEqual(attendance.working_hours, 1.5)

	def test_working_hours_threshold_for_absent_and_half_day_1(self):
		# considers half day over absent
		from erpnext.hr.doctype.employee_checkin.test_employee_checkin import make_checkin

		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")
		shift_type = setup_shift_type(
			shift_type="Half Day + Absent Test",
			working_hours_threshold_for_half_day=1,
			working_hours_threshold_for_absent=2,
		)
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		timestamp = datetime.combine(date, get_time("08:00:00"))
		log_in = make_checkin(employee, timestamp)
		self.assertEqual(log_in.shift, shift_type.name)

		timestamp = datetime.combine(date, get_time("08:45:00"))
		log_out = make_checkin(employee, timestamp)
		self.assertEqual(log_out.shift, shift_type.name)

		shift_type.process_auto_attendance()

		attendance = frappe.db.get_value(
			"Attendance", {"shift": shift_type.name}, ["status", "working_hours"], as_dict=True
		)
		self.assertEqual(attendance.status, "Half Day")
		self.assertEqual(attendance.working_hours, 0.75)

	def test_working_hours_threshold_for_absent_and_half_day_2(self):
		# considers absent over half day
		from erpnext.hr.doctype.employee_checkin.test_employee_checkin import make_checkin

		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")
		shift_type = setup_shift_type(
			shift_type="Half Day + Absent Test",
			working_hours_threshold_for_half_day=1,
			working_hours_threshold_for_absent=2,
		)
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		timestamp = datetime.combine(date, get_time("08:00:00"))
		log_in = make_checkin(employee, timestamp)
		self.assertEqual(log_in.shift, shift_type.name)

		timestamp = datetime.combine(date, get_time("09:30:00"))
		log_out = make_checkin(employee, timestamp)
		self.assertEqual(log_out.shift, shift_type.name)

		shift_type.process_auto_attendance()

		attendance = frappe.db.get_value("Attendance", {"shift": shift_type.name}, "status")
		self.assertEqual(attendance, "Absent")

	def test_mark_absent_for_dates_with_no_attendance(self):
		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")
		shift_type = setup_shift_type(shift_type="Test Absent with no Attendance")

		# absentees are auto-marked one day after to wait for any manual attendance records
		date = add_days(getdate(), -1)
		make_shift_assignment(shift_type.name, employee, date)

		shift_type.process_auto_attendance()

		attendance = frappe.db.get_value(
			"Attendance", {"attendance_date": date, "employee": employee}, "status"
		)
		self.assertEqual(attendance, "Absent")

	@set_holiday_list("Salary Slip Test Holiday List", "_Test Company")
	def test_skip_marking_absent_on_a_holiday(self):
		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")
		shift_type = setup_shift_type(shift_type="Test Absent with no Attendance")
		shift_type.holiday_list = None
		shift_type.save()

		# should not mark any attendance if no shift assignment is created
		shift_type.process_auto_attendance()
		attendance = frappe.db.get_value("Attendance", {"employee": employee}, "status")
		self.assertIsNone(attendance)

		first_sunday = get_first_sunday(self.holiday_list, for_date=getdate())
		make_shift_assignment(shift_type.name, employee, first_sunday)

		shift_type.process_auto_attendance()

		attendance = frappe.db.get_value(
			"Attendance", {"attendance_date": first_sunday, "employee": employee}, "status"
		)
		self.assertIsNone(attendance)

	def test_get_start_and_end_dates(self):
		date = getdate()

		doj = add_days(date, -30)
		relieving_date = add_days(date, -5)
		employee = make_employee(
			"test_employee_dates@example.com",
			company="_Test Company",
			date_of_joining=doj,
			relieving_date=relieving_date,
		)
		shift_type = setup_shift_type(
			shift_type="Test Absent with no Attendance", process_attendance_after=add_days(doj, 2)
		)

		make_shift_assignment(shift_type.name, employee, add_days(date, -25))

		shift_type.process_auto_attendance()

		# should not mark absent before shift assignment/process attendance after date
		attendance = frappe.db.get_value(
			"Attendance", {"attendance_date": doj, "employee": employee}, "name"
		)
		self.assertIsNone(attendance)

		# mark absent on Relieving Date
		attendance = frappe.db.get_value(
			"Attendance", {"attendance_date": relieving_date, "employee": employee}, "status"
		)
		self.assertEquals(attendance, "Absent")

		# should not mark absent after Relieving Date
		attendance = frappe.db.get_value(
			"Attendance", {"attendance_date": add_days(relieving_date, 1), "employee": employee}, "name"
		)
		self.assertIsNone(attendance)

	def test_skip_auto_attendance_for_duplicate_record(self):
		# Skip auto attendance in case of duplicate attendance record
		from erpnext.hr.doctype.attendance.attendance import mark_attendance
		from erpnext.hr.doctype.employee_checkin.test_employee_checkin import make_checkin

		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")

		shift_type = setup_shift_type()
		date = getdate()

		# mark attendance
		mark_attendance(employee, date, "Present")
		make_shift_assignment(shift_type.name, employee, date)

		timestamp = datetime.combine(date, get_time("08:00:00"))
		log_in = make_checkin(employee, timestamp)
		self.assertEqual(log_in.shift, shift_type.name)

		timestamp = datetime.combine(date, get_time("12:00:00"))
		log_out = make_checkin(employee, timestamp)
		self.assertEqual(log_out.shift, shift_type.name)

		# auto attendance should skip marking
		shift_type.process_auto_attendance()

		log_in.reload()
		log_out.reload()
		self.assertEqual(log_in.skip_auto_attendance, 1)
		self.assertEqual(log_out.skip_auto_attendance, 1)

	def test_skip_auto_attendance_for_overlapping_shift(self):
		# Skip auto attendance in case of overlapping shift attendance record
		# this case won't occur in case of shift assignment, since it will not allow overlapping shifts to be assigned
		# can happen if manual attendance records are created
		from erpnext.hr.doctype.attendance.attendance import mark_attendance
		from erpnext.hr.doctype.employee_checkin.test_employee_checkin import make_checkin

		employee = make_employee("test_employee_checkin@example.com", company="_Test Company")
		shift_1 = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="10:00:00")
		shift_2 = setup_shift_type(shift_type="Shift 2", start_time="09:30:00", end_time="11:00:00")

		date = getdate()

		# mark attendance
		mark_attendance(employee, date, "Present", shift=shift_1.name)
		make_shift_assignment(shift_2.name, employee, date)

		timestamp = datetime.combine(date, get_time("09:30:00"))
		log_in = make_checkin(employee, timestamp)
		self.assertEqual(log_in.shift, shift_2.name)

		timestamp = datetime.combine(date, get_time("11:00:00"))
		log_out = make_checkin(employee, timestamp)
		self.assertEqual(log_out.shift, shift_2.name)

		# auto attendance should be skipped for shift 2
		# since it is already marked for overlapping shift 1
		shift_2.process_auto_attendance()

		log_in.reload()
		log_out.reload()
		self.assertEqual(log_in.skip_auto_attendance, 1)
		self.assertEqual(log_out.skip_auto_attendance, 1)


def setup_shift_type(**args):
	args = frappe._dict(args)
	date = getdate()

	shift_type = frappe.get_doc(
		{
			"doctype": "Shift Type",
			"__newname": args.shift_type or "_Test Shift",
			"start_time": "08:00:00",
			"end_time": "12:00:00",
			"enable_auto_attendance": 1,
			"determine_check_in_and_check_out": "Alternating entries as IN and OUT during the same shift",
			"working_hours_calculation_based_on": "First Check-in and Last Check-out",
			"begin_check_in_before_shift_start_time": 60,
			"allow_check_out_after_shift_end_time": 60,
			"process_attendance_after": add_days(date, -2),
			"last_sync_of_checkin": now_datetime() + timedelta(days=1),
		}
	)

	holiday_list = "Employee Checkin Test Holiday List"
	if not frappe.db.exists("Holiday List", "Employee Checkin Test Holiday List"):
		holiday_list = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": "Employee Checkin Test Holiday List",
				"from_date": get_year_start(date),
				"to_date": get_year_ending(date),
			}
		).insert()
		holiday_list = holiday_list.name

	shift_type.holiday_list = holiday_list
	shift_type.update(args)
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

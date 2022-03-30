# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_year_ending, get_year_start, getdate, now_datetime, nowdate

from erpnext.hr.doctype.attendance.attendance import (
	get_month_map,
	get_unmarked_days,
	mark_attendance,
)
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.leave_application.test_leave_application import get_first_sunday

test_records = frappe.get_test_records("Attendance")


class TestAttendance(FrappeTestCase):
	def setUp(self):
		from erpnext.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list

		from_date = get_year_start(getdate())
		to_date = get_year_ending(getdate())
		self.holiday_list = make_holiday_list(from_date=from_date, to_date=to_date)

	def test_mark_absent(self):
		employee = make_employee("test_mark_absent@example.com")
		date = nowdate()
		frappe.db.delete("Attendance", {"employee": employee, "attendance_date": date})
		attendance = mark_attendance(employee, date, "Absent")
		fetch_attendance = frappe.get_value(
			"Attendance", {"employee": employee, "attendance_date": date, "status": "Absent"}
		)
		self.assertEqual(attendance, fetch_attendance)

	def test_unmarked_days(self):
		now = now_datetime()
		previous_month = now.month - 1
		first_day = now.replace(day=1).replace(month=previous_month).date()

		employee = make_employee(
			"test_unmarked_days@example.com", date_of_joining=add_days(first_day, -1)
		)
		frappe.db.delete("Attendance", {"employee": employee})
		frappe.db.set_value("Employee", employee, "holiday_list", self.holiday_list)

		first_sunday = get_first_sunday(self.holiday_list, for_date=first_day)
		mark_attendance(employee, first_day, "Present")
		month_name = get_month_name(first_day)

		unmarked_days = get_unmarked_days(employee, month_name)
		unmarked_days = [getdate(date) for date in unmarked_days]

		# attendance already marked for the day
		self.assertNotIn(first_day, unmarked_days)
		# attendance unmarked
		self.assertIn(getdate(add_days(first_day, 1)), unmarked_days)
		# holiday considered in unmarked days
		self.assertIn(first_sunday, unmarked_days)

	def test_unmarked_days_excluding_holidays(self):
		now = now_datetime()
		previous_month = now.month - 1
		first_day = now.replace(day=1).replace(month=previous_month).date()

		employee = make_employee(
			"test_unmarked_days@example.com", date_of_joining=add_days(first_day, -1)
		)
		frappe.db.delete("Attendance", {"employee": employee})

		frappe.db.set_value("Employee", employee, "holiday_list", self.holiday_list)

		first_sunday = get_first_sunday(self.holiday_list, for_date=first_day)
		mark_attendance(employee, first_day, "Present")
		month_name = get_month_name(first_day)

		unmarked_days = get_unmarked_days(employee, month_name, exclude_holidays=True)
		unmarked_days = [getdate(date) for date in unmarked_days]

		# attendance already marked for the day
		self.assertNotIn(first_day, unmarked_days)
		# attendance unmarked
		self.assertIn(getdate(add_days(first_day, 1)), unmarked_days)
		# holidays not considered in unmarked days
		self.assertNotIn(first_sunday, unmarked_days)

	def test_unmarked_days_as_per_joining_and_relieving_dates(self):
		now = now_datetime()
		previous_month = now.month - 1
		first_day = now.replace(day=1).replace(month=previous_month).date()

		doj = add_days(first_day, 1)
		relieving_date = add_days(first_day, 5)
		employee = make_employee(
			"test_unmarked_days_as_per_doj@example.com", date_of_joining=doj, relieving_date=relieving_date
		)
		frappe.db.delete("Attendance", {"employee": employee})

		frappe.db.set_value("Employee", employee, "holiday_list", self.holiday_list)

		attendance_date = add_days(first_day, 2)
		mark_attendance(employee, attendance_date, "Present")
		month_name = get_month_name(first_day)

		unmarked_days = get_unmarked_days(employee, month_name)
		unmarked_days = [getdate(date) for date in unmarked_days]

		# attendance already marked for the day
		self.assertNotIn(attendance_date, unmarked_days)
		# date before doj not in unmarked days
		self.assertNotIn(add_days(doj, -1), unmarked_days)
		# date after relieving not in unmarked days
		self.assertNotIn(add_days(relieving_date, 1), unmarked_days)

	def tearDown(self):
		frappe.db.rollback()


def get_month_name(date):
	month_number = date.month
	for month, number in get_month_map().items():
		if number == month_number:
			return month

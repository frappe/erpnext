# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, add_months, getdate

from erpnext import get_default_company
from erpnext.education.doctype.student.test_student import create_student
from erpnext.education.doctype.student_group.test_student_group import get_random_group


class TestStudentLeaveApplication(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabStudent Leave Application`""")
		create_holiday_list()

	def test_attendance_record_creation(self):
		leave_application = create_leave_application()
		attendance_record = frappe.db.exists(
			"Student Attendance", {"leave_application": leave_application.name, "status": "Absent"}
		)
		self.assertTrue(attendance_record)

		# mark as present
		date = add_days(getdate(), -1)
		leave_application = create_leave_application(date, date, 1)
		attendance_record = frappe.db.exists(
			"Student Attendance", {"leave_application": leave_application.name, "status": "Present"}
		)
		self.assertTrue(attendance_record)

	def test_attendance_record_updated(self):
		attendance = create_student_attendance()
		create_leave_application()
		self.assertEqual(frappe.db.get_value("Student Attendance", attendance.name, "status"), "Absent")

	def test_attendance_record_cancellation(self):
		leave_application = create_leave_application()
		leave_application.cancel()
		attendance_status = frappe.db.get_value(
			"Student Attendance", {"leave_application": leave_application.name}, "docstatus"
		)
		self.assertTrue(attendance_status, 2)

	def test_holiday(self):
		today = getdate()
		leave_application = create_leave_application(
			from_date=today, to_date=add_days(today, 1), submit=0
		)

		# holiday list validation
		company = get_default_company() or frappe.get_all("Company")[0].name
		frappe.db.set_value("Company", company, "default_holiday_list", "")
		self.assertRaises(frappe.ValidationError, leave_application.save)

		frappe.db.set_value("Company", company, "default_holiday_list", "Test Holiday List for Student")
		leave_application.save()

		leave_application.reload()
		self.assertEqual(leave_application.total_leave_days, 1)

		# check no attendance record created for a holiday
		leave_application.submit()
		self.assertIsNone(
			frappe.db.exists(
				"Student Attendance", {"leave_application": leave_application.name, "date": add_days(today, 1)}
			)
		)

	def tearDown(self):
		company = get_default_company() or frappe.get_all("Company")[0].name
		frappe.db.set_value("Company", company, "default_holiday_list", "_Test Holiday List")


def create_leave_application(from_date=None, to_date=None, mark_as_present=0, submit=1):
	student = get_student()

	leave_application = frappe.new_doc("Student Leave Application")
	leave_application.student = student.name
	leave_application.attendance_based_on = "Student Group"
	leave_application.student_group = get_random_group().name
	leave_application.from_date = from_date if from_date else getdate()
	leave_application.to_date = from_date if from_date else getdate()
	leave_application.mark_as_present = mark_as_present

	if submit:
		leave_application.insert()
		leave_application.submit()

	return leave_application


def create_student_attendance(date=None, status=None):
	student = get_student()
	attendance = frappe.get_doc(
		{
			"doctype": "Student Attendance",
			"student": student.name,
			"status": status if status else "Present",
			"date": date if date else getdate(),
			"student_group": get_random_group().name,
		}
	).insert()
	return attendance


def get_student():
	return create_student(
		dict(email="test_student@gmail.com", first_name="Test", last_name="Student")
	)


def create_holiday_list():
	holiday_list = "Test Holiday List for Student"
	today = getdate()
	if not frappe.db.exists("Holiday List", holiday_list):
		frappe.get_doc(
			dict(
				doctype="Holiday List",
				holiday_list_name=holiday_list,
				from_date=add_months(today, -6),
				to_date=add_months(today, 6),
				holidays=[dict(holiday_date=add_days(today, 1), description="Test")],
			)
		).insert()

	company = get_default_company() or frappe.get_all("Company")[0].name
	frappe.db.set_value("Company", company, "default_holiday_list", holiday_list)
	return holiday_list

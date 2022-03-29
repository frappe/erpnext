# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt

import unittest

import frappe

from erpnext.education.doctype.program.test_program import make_program_and_linked_courses

test_records = frappe.get_test_records("Student")


class TestStudent(unittest.TestCase):
	def setUp(self):
		create_student(
			{
				"first_name": "_Test Name",
				"last_name": "_Test Last Name",
				"email": "_test_student@example.com",
			}
		)
		make_program_and_linked_courses("_Test Program 1", ["_Test Course 1", "_Test Course 2"])

	def test_create_student_user(self):
		self.assertTrue(bool(frappe.db.exists("User", "_test_student@example.com")))
		frappe.db.rollback()

	def test_enroll_in_program(self):
		student = get_student("_test_student@example.com")
		enrollment = student.enroll_in_program("_Test Program 1")
		test_enrollment = frappe.get_all(
			"Program Enrollment", filters={"student": student.name, "Program": "_Test Program 1"}
		)
		self.assertTrue(len(test_enrollment))
		self.assertEqual(test_enrollment[0]["name"], enrollment.name)
		frappe.db.rollback()

	def test_get_program_enrollments(self):
		student = get_student("_test_student@example.com")
		enrollment = student.enroll_in_program("_Test Program 1")
		program_enrollments = student.get_program_enrollments()
		self.assertTrue("_Test Program 1" in program_enrollments)
		frappe.db.rollback()

	def test_get_all_course_enrollments(self):
		student = get_student("_test_student@example.com")
		enrollment = student.enroll_in_program("_Test Program 1")
		course_enrollments = student.get_all_course_enrollments()
		self.assertTrue("_Test Course 1" in course_enrollments.keys())
		self.assertTrue("_Test Course 2" in course_enrollments.keys())
		frappe.db.rollback()

	def tearDown(self):
		for entry in frappe.db.get_all("Course Enrollment"):
			frappe.delete_doc("Course Enrollment", entry.name)

		for entry in frappe.db.get_all("Program Enrollment"):
			doc = frappe.get_doc("Program Enrollment", entry.name)
			doc.cancel()
			doc.delete()


def create_student(student_dict):
	student = get_student(student_dict["email"])
	if not student:
		student = frappe.get_doc(
			{
				"doctype": "Student",
				"first_name": student_dict["first_name"],
				"last_name": student_dict["last_name"],
				"student_email_id": student_dict["email"],
			}
		).insert()
	return student


def get_student(email):
	try:
		student_id = frappe.get_all("Student", {"student_email_id": email}, ["name"])[0].name
		return frappe.get_doc("Student", student_id)
	except IndexError:
		return None

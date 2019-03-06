# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals
from frappe.test_runner import make_test_records
from erpnext.education.doctype.program.test_program import make_program_and_linked_courses

import frappe
import unittest

test_records = frappe.get_test_records('Student')
class TestStudent(unittest.TestCase):
	def setUp(self):
		create_student({"first_name": "_Test Name", "last_name": "_Test Last Name", "email": "_test_student@example.com"})

	def test_create_student_user(self):
		self.assertTrue(bool(frappe.db.exists("User", "_test_student@example.com")))
		frappe.db.rollback()

def create_student(student_dict):
	student = get_student(student_dict['email'])
	if not student:
		student = frappe.get_doc({
			"doctype": "Student",
			"first_name": student_dict['first_name'],
			"last_name": student_dict['last_name'],
			"student_email_id": student_dict['email']
		}).insert()
	return student

def get_student(email):
	try:
		student_id = frappe.get_all("Student", {"student_email_id": email}, ["name"])[0].name
		return frappe.get_doc("Student", student_id)
	except IndexError:
		return None
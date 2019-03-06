# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals
from erpnext.education.doctype.course.test_course import make_course

import frappe
import unittest

# test_records = frappe.get_test_records('Program')

class TestProgram(unittest.TestCase):
	def setUp(self):
		make_program_and_linked_courses("_Test Program 1", ["_Test Course 1", "_Test Course 2"])

	def test_get_course_list(self):
		program = frappe.get_doc("Program", "_Test Program 1")
		course = program.get_course_list()
		self.assertEqual(course[0].name, "_Test Course 1")
		self.assertEqual(course[1].name, "_Test Course 2")
		frappe.db.rollback()

def make_program(name):
	program = frappe.get_doc({
		"doctype": "Program",
		"program_name": name,
		"program_code": name,
		"is_published": True,
		"is_featured": True,
	}).insert()
	return program.name

def make_program_and_linked_courses(program_name, course_name_list):
	try:
		program = frappe.get_doc("Program", program_name)
	except frappe.DoesNotExistError:
		make_program(program_name)
		program = frappe.get_doc("Program", program_name)
	course_list = [make_course(course_name) for course_name in course_name_list]
	for course in course_list:
		program.append("courses", {"course": course})
	program.save()
	return program


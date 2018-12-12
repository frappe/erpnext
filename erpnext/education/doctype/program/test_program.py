# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals
from erpnext.education.doctype.course.test_course import make_course

import frappe
import unittest

# test_records = frappe.get_test_records('Program')

class TestProgram(unittest.TestCase):
	pass


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
	return program.name


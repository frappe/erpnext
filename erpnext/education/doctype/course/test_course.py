# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

# test_records = frappe.get_test_records('Course')

class TestCourse(unittest.TestCase):
	pass

def make_course(name):
	course = frappe.get_doc({
		"doctype": "Program",
		"course_name": name,
		"course_code": name
	}).insert()
	return course.name
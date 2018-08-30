# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.make_random import get_random
import erpnext.education

def get_random_group():
	doc = frappe.get_doc({
		"doctype": "Student Group",
		"student_group_name": "_Test Student Group R",
		"group_based_on": "Activity"
		}).insert()

	student_list = []
	while len(student_list) < 3:
		s = get_random("Student")
		if s not in student_list:
			student_list.append(s)

	doc.extend("students", [{"student":d} for d in student_list])
	doc.save()

	return doc

class TestStudentGroup(unittest.TestCase):
	def test_student_roll_no(self):
		doc = get_random_group()
		self.assertEqual(max([d.group_roll_number for d in doc.students]), 3)

	def test_in_group(self):
		doc = get_random_group()

		last_student = doc.students[-1].student

		# remove last student
		doc.students = doc.students[:-1]
		doc.save()

		self.assertRaises(erpnext.education.StudentNotInGroupError,
			erpnext.education.validate_student_belongs_to_group, last_student, doc.name)

		# safe, don't throw validation
		erpnext.education.validate_student_belongs_to_group(doc.students[0].student, doc.name)
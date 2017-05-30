# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.make_random import get_random

class TestStudentGroup(unittest.TestCase):
	 def test_student_roll_no(self):
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
	 	self.assertEquals(max([d.group_roll_number for d in doc.students]), 3)


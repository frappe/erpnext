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
	pass

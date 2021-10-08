# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

from erpnext.education.api import get_grade

# test_records = frappe.get_test_records('Assessment Result')

class TestAssessmentResult(unittest.TestCase):
	def test_grade(self):
		grade = get_grade("_Test Grading Scale", 80)
		self.assertEqual("A", grade)

		grade = get_grade("_Test Grading Scale", 70)
		self.assertEqual("B", grade)

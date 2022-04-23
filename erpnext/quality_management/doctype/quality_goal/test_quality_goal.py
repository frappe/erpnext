# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.quality_management.doctype.quality_procedure.test_quality_procedure import create_procedure

class TestQualityGoal(unittest.TestCase):
	def test_quality_goal(self):
		# no code, just a basic sanity check
		goal = get_quality_goal()
		self.assertTrue(goal)
		goal.delete()

def get_quality_goal():
	return frappe.get_doc(dict(
		doctype = 'Quality Goal',
		goal = 'Test Quality Module',
		frequency = 'Daily',
		objectives = [
			dict(objective = 'Check test cases', target='100', uom='Percent')
		]
	)).insert()
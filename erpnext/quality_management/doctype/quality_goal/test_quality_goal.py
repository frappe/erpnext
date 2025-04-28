# Copyright (c) 2018, Frappe and Contributors
# See license.txt
<<<<<<< HEAD
import unittest

import frappe
from frappe.tests import IntegrationTestCase


class TestQualityGoal(IntegrationTestCase):
=======

import unittest

import frappe


class TestQualityGoal(unittest.TestCase):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	def test_quality_goal(self):
		# no code, just a basic sanity check
		goal = get_quality_goal()
		self.assertTrue(goal)
		goal.delete()


def get_quality_goal():
	return frappe.get_doc(
		dict(
			doctype="Quality Goal",
			goal="Test Quality Module",
			frequency="Daily",
			objectives=[dict(objective="Check test cases", target="100", uom="Percent")],
		)
	).insert()

# Copyright (c) 2018, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.quality_management.doctype.quality_review.quality_review import review


class TestQualityGoal(FrappeTestCase):
	def test_quality_goal(self):
		# no code, just a basic sanity check
		goal = get_quality_goal()
		self.assertTrue(goal)
		goal.delete()

	def test_quarterly_goal_reviewed_on_its_date(self):
		goal = frappe.get_doc(
			doctype="Quality Goal",
			goal="Test Quarterly Goal",
			frequency="Quarterly",
			date="15",
			objectives=[dict(objective="Check test cases")],
		).insert()

		for day in ("2027-04-01", "2027-04-15"):
			with self.freeze_time(day):
				review()

		self.assertEqual(
			frappe.get_all("Quality Review", {"goal": goal.name}, pluck="date"),
			[frappe.utils.getdate("2027-04-15")],
		)


def get_quality_goal(goal="Test Quality Module"):
	return frappe.get_doc(
		doctype="Quality Goal",
		goal=goal,
		frequency="Daily",
		objectives=[dict(objective="Check test cases", target="100", uom="Percent")],
	).insert()

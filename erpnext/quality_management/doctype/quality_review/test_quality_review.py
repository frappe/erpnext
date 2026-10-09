# Copyright (c) 2018, Frappe and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite

from ..quality_goal.test_quality_goal import get_quality_goal
from .quality_review import create_review, review


class TestQualityReview(ERPNextTestSuite):
	def test_review_creation(self):
		quality_goal = get_quality_goal()
		review()

		# check if review exists
		quality_review = frappe.get_doc("Quality Review", dict(goal=quality_goal.name))
		self.assertEqual(quality_goal.objectives[0].target, quality_review.reviews[0].target)
		quality_review.delete()

		quality_goal.delete()

	def test_scheduled_review_is_open(self):
		quality_goal = get_quality_goal()
		create_review(quality_goal.name)

		quality_review = frappe.get_doc("Quality Review", {"goal": quality_goal.name})
		self.assertEqual(quality_review.status, "Open")
		self.assertEqual(quality_review.reviews[0].status, "Open")

	def test_objectives_must_belong_to_goal(self):
		quality_goal = get_quality_goal()
		other_goal = frappe.get_doc(
			doctype="Quality Goal", goal="Test Scrap Rate", objectives=[dict(objective="Scrap rate")]
		).insert()

		made_up = frappe.get_doc(
			doctype="Quality Review",
			goal=quality_goal.name,
			reviews=[dict(objective="Anything", status="Passed")],
		)
		self.assertRaises(frappe.ValidationError, made_up.insert)

		quality_review = frappe.get_doc(doctype="Quality Review", goal=quality_goal.name).insert()
		quality_review.goal = other_goal.name
		self.assertRaises(frappe.ValidationError, quality_review.save)

	def test_objectives_follow_unchanged_goal(self):
		quality_goal = get_quality_goal()
		quality_review = frappe.get_doc(doctype="Quality Review", goal=quality_goal.name).insert()

		quality_review.reviews[0].objective = "Anything"
		quality_review.reviews[0].status = "Passed"
		self.assertRaises(frappe.ValidationError, quality_review.save)

	def test_review_job_runs_once_a_day(self):
		quality_goal = get_quality_goal()
		review()
		review()

		self.assertEqual(frappe.db.count("Quality Review", {"goal": quality_goal.name}), 1)

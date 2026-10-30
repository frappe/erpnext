import frappe
from frappe.desk.query_report import run

from erpnext.quality_management.doctype.quality_goal.test_quality_goal import get_quality_goal
from erpnext.tests.utils import ERPNextTestSuite


class TestReview(ERPNextTestSuite):
	def test_lists_actions_raised_from_reviews(self):
		review = frappe.get_doc(doctype="Quality Review", goal=get_quality_goal().name).insert()
		from_review = frappe.get_doc(doctype="Quality Action", review=review.name).insert()
		without_review = frappe.get_doc(doctype="Quality Action").insert()

		actions = [row["name"] for row in run("Review")["result"]]
		self.assertIn(from_review.name, actions)
		self.assertNotIn(without_review.name, actions)

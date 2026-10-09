# Copyright (c) 2018, Frappe and Contributors
# See license.txt

import frappe

from erpnext.quality_management.doctype.quality_goal.test_quality_goal import get_quality_goal
from erpnext.quality_management.doctype.quality_procedure.test_quality_procedure import create_procedure
from erpnext.tests.utils import ERPNextTestSuite


class TestQualityAction(ERPNextTestSuite):
	def test_action_without_resolutions_is_open(self):
		action = frappe.get_doc(doctype="Quality Action", corrective_preventive="Corrective").insert()
		self.assertEqual(action.status, "Open")

		action.append("resolutions", dict(problem="Late delivery", status="Completed"))
		action.save()
		self.assertEqual(action.status, "Completed")

	def test_procedure_fetched_from_review(self):
		quality_goal = get_quality_goal()
		quality_goal.procedure = create_procedure().name
		quality_goal.save()
		review = frappe.get_doc(doctype="Quality Review", goal=quality_goal.name).insert()

		action = frappe.get_doc(doctype="Quality Action", review=review.name).insert()
		self.assertEqual(action.procedure, quality_goal.procedure)

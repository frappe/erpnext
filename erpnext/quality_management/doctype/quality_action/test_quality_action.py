# Copyright (c) 2018, Frappe and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestQualityAction(ERPNextTestSuite):
	def test_action_without_resolutions_is_open(self):
		action = frappe.get_doc(doctype="Quality Action", corrective_preventive="Corrective").insert()
		self.assertEqual(action.status, "Open")

		action.append("resolutions", dict(problem="Late delivery", status="Completed"))
		action.save()
		self.assertEqual(action.status, "Completed")

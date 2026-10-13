# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.desk.search import search_link
from frappe.tests.utils import FrappeTestCase

from erpnext.tests.permission_test_utils import as_user, make_fenced_user


class TestQualityFeedback(unittest.TestCase):
	def test_quality_feedback(self):
		template = frappe.get_doc(
			dict(
				doctype="Quality Feedback Template",
				template="Test Template",
				parameters=[dict(parameter="Test Parameter 1"), dict(parameter="Test Parameter 2")],
			)
		).insert()

		feedback = frappe.get_doc(
			dict(
				doctype="Quality Feedback",
				template=template.name,
				document_type="User",
				document_name=frappe.session.user,
			)
		).insert()

		self.assertEqual(template.parameters[0].parameter, feedback.parameters[0].parameter)

		feedback.delete()
		template.delete()


class TestQualityFeedbackTemplateAccess(FrappeTestCase):
	def test_quality_manager_can_pick_a_template(self):
		template = frappe.get_doc(
			doctype="Quality Feedback Template",
			template="_Test Template Access",
			parameters=[dict(parameter="Test Parameter 1")],
		).insert()
		quality_manager = make_fenced_user("quality-feedback-manager@example.com", ["Quality Manager"])

		with as_user(quality_manager):
			templates = [row["value"] for row in search_link("Quality Feedback Template", "_Test Template")]

		self.assertIn(template.name, templates)

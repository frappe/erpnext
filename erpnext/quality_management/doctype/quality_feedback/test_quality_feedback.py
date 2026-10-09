# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.desk.search import search_link

from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestQualityFeedback(ERPNextTestSuite):
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

	def test_quality_feedback(self):
		template = frappe.get_doc(
			doctype="Quality Feedback Template",
			template="Test Template",
			parameters=[dict(parameter="Test Parameter 1"), dict(parameter="Test Parameter 2")],
		).insert()

		feedback = frappe.get_doc(
			doctype="Quality Feedback",
			template=template.name,
			document_type="User",
			document_name=frappe.session.user,
		).insert()

		self.assertEqual(template.parameters[0].parameter, feedback.parameters[0].parameter)

		feedback.delete()
		template.delete()

	def test_parameters_follow_template(self):
		first = make_template("Test Template", ["Quality", "Delivery"])
		second = make_template("Test Template 2", ["Packaging"])

		made_up = frappe.get_doc(
			doctype="Quality Feedback",
			template=first.name,
			parameters=[dict(parameter="Made up", rating="5")],
		)
		self.assertRaises(frappe.ValidationError, made_up.insert)

		feedback = frappe.get_doc(doctype="Quality Feedback", template=first.name).insert()
		feedback.template = second.name
		self.assertRaises(frappe.ValidationError, feedback.save)

		feedback.reload()
		feedback.template = second.name
		feedback.set_parameters()
		feedback.save()
		self.assertEqual([d.parameter for d in feedback.parameters], ["Packaging"])

	def test_parameters_start_unrated(self):
		template = make_template("Test Template", ["Quality"])
		feedback = frappe.get_doc(doctype="Quality Feedback", template=template.name).insert()
		self.assertFalse(feedback.parameters[0].rating)


def make_template(name, parameters):
	return frappe.get_doc(
		doctype="Quality Feedback Template",
		template=name,
		parameters=[dict(parameter=parameter) for parameter in parameters],
	).insert()

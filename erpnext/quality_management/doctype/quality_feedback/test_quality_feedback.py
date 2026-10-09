# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestQualityFeedback(FrappeTestCase):
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

	def test_parameters_follow_template(self):
		first = make_template("Test Follow Template", ["Quality", "Delivery"])
		second = make_template("Test Follow Template 2", ["Packaging"])

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

	def test_parameters_follow_unchanged_template(self):
		template = make_template("Test Unchanged Template", ["Quality", "Delivery"])
		feedback = frappe.get_doc(doctype="Quality Feedback", template=template.name).insert()

		feedback.parameters[0].parameter = "Made up"
		self.assertRaises(frappe.ValidationError, feedback.save)

		feedback.reload()
		feedback.append("parameters", {})
		self.assertRaises(frappe.ValidationError, feedback.save)

	def test_parameters_start_unrated(self):
		template = make_template("Test Unrated Template", ["Quality"])
		feedback = frappe.get_doc(doctype="Quality Feedback", template=template.name).insert()
		self.assertFalse(feedback.parameters[0].rating)


def make_template(name, parameters):
	return frappe.get_doc(
		doctype="Quality Feedback Template",
		template=name,
		parameters=[dict(parameter=parameter) for parameter in parameters],
	).insert()

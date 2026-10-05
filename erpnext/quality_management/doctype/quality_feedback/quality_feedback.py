# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class QualityFeedback(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.quality_management.doctype.quality_feedback_parameter.quality_feedback_parameter import (
			QualityFeedbackParameter,
		)

		document_name: DF.DynamicLink
		document_type: DF.Literal["User", "Customer"]
		parameters: DF.Table[QualityFeedbackParameter]
		template: DF.Link
	# end: auto-generated types

	@frappe.whitelist()
	def set_parameters(self):
		if not self.template:
			return

		self.set("parameters", [])
		for d in frappe.get_doc("Quality Feedback Template", self.template).parameters:
			self.append("parameters", dict(parameter=d.parameter))

	def validate(self):
		if not self.document_name:
			self.document_type = "User"
			self.document_name = frappe.session.user

		if not self.parameters:
			self.set_parameters()
		elif self.has_value_changed("template"):
			self.validate_parameters()

	def validate_parameters(self):
		parameters = frappe.get_all(
			"Quality Feedback Template Parameter",
			filters={"parent": self.template, "parenttype": "Quality Feedback Template"},
			pluck="parameter",
		)
		for d in self.parameters:
			if d.parameter not in parameters:
				frappe.throw(
					_("Row #{0}: Parameter {1} is not part of Quality Feedback Template {2}").format(
						d.idx, frappe.bold(d.parameter), frappe.bold(self.template)
					)
				)

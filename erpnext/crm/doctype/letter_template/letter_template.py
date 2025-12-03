# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils.jinja import validate_template


class LetterTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		content: DF.TextEditor
		letter_type: DF.Link
		subject: DF.Data
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if self.subject:
			validate_template(self.subject)
		if self.content:
			validate_template(self.content)


@frappe.whitelist()
def get_letter_template(template_name, doc):
	if isinstance(doc, str):
		try:
			doc = json.loads(doc)
		except json.JSONDecodeError:
			frappe.throw(frappe._("Invalid document data"))

	template = frappe.get_doc("Letter Template", template_name)

	subject = None
	content = None

	if template.subject:
		subject = frappe.render_template(template.subject, doc)

	if template.content:
		content = frappe.render_template(template.content, doc)

	return {"subject": subject, "content": content}

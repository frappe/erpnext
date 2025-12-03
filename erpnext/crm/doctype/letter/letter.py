# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Letter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.TextEditor | None
		content: DF.TextEditor | None
		date: DF.Date
		language: DF.Data | None
		letter_head: DF.Link | None
		letter_template: DF.Link | None
		letter_type: DF.Link
		naming_series: DF.Literal["L-.YY.-"]
		recipient: DF.DynamicLink
		recipient_address: DF.Link | None
		recipient_name: DF.Data | None
		recipient_type: DF.Literal["Customer", "Supplier", "Employee", "Shareholder", "Contact"]
		subject: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.set_recipient_name()

	def set_recipient_name(self):
		if self.recipient_type and self.recipient:
			name_field = self.get_recipient_name_field()
			if frappe.db.has_column(self.recipient_type, name_field):
				self.recipient_name = frappe.db.get_value(self.recipient_type, self.recipient, name_field)
			else:
				self.recipient_name = frappe.db.get_value(self.recipient_type, self.recipient, "name")

	def get_recipient_name_field(self):
		if self.recipient_type == "Shareholder":
			return "title"
		elif self.recipient_type == "Contact":
			return "full_name"
		else:
			return self.recipient_type.lower() + "_name"


@frappe.whitelist()
def get_recipient_details(recipient_type: str, recipient: str):
	if not recipient_type or not recipient:
		return {}

	if not frappe.db.exists(recipient_type, recipient):
		frappe.throw(_("{0} {1} does not exist").format(recipient_type, recipient))

	if not frappe.has_permission(recipient_type, doc=recipient):
		frappe.throw(
			_("Not permitted to access {0} {1}").format(recipient_type, recipient),
			frappe.PermissionError,
		)

	name_field = (
		"title"
		if recipient_type == "Shareholder"
		else ("full_name" if recipient_type == "Contact" else recipient_type.lower() + "_name")
	)

	if frappe.db.has_column(recipient_type, name_field):
		recipient_name = frappe.db.get_value(recipient_type, recipient, name_field)
	else:
		recipient_name = frappe.db.get_value(recipient_type, recipient, "name")

	# Get language from recipient if available
	language = None
	if frappe.db.has_column(recipient_type, "language"):
		language = frappe.db.get_value(recipient_type, recipient, "language")

	return {"recipient_name": recipient_name, "language": language}

# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.address_and_contact import delete_contact_and_address, load_address_and_contact
from frappe.model.document import Document


class FinancialInstitution(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		country: DF.Link | None
		institution_name: DF.Data
		institution_type: DF.Literal["Bank", "AMC", "Corporate Issuer", "Custodian", "Broker", "Government"]
		is_active: DF.Check
		primary_contact: DF.Link | None
		registration_number: DF.Data | None
	# end: auto-generated types

	def onload(self):
		load_address_and_contact(self)

	def on_update(self):
		self.link_primary_contact()

	def link_primary_contact(self):
		"""The Primary Contact is linked to this institution, so it also shows under Contacts."""
		if not self.primary_contact:
			return

		contact = frappe.get_doc("Contact", self.primary_contact)
		if not contact.has_link(self.doctype, self.name):
			contact.append("links", {"link_doctype": self.doctype, "link_name": self.name})
			contact.save()

	def on_trash(self):
		delete_contact_and_address(self.doctype, self.name)

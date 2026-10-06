# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.address_and_contact import delete_contact_and_address, load_address_and_contact
from frappe.model.document import Document


class FinancialInstitution(Document):
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
			contact.save(ignore_permissions=True)

	def on_trash(self):
		delete_contact_and_address(self.doctype, self.name)

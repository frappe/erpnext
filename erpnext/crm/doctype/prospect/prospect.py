# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class Prospect(Document):
	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		self.update_lead_details()

	def on_update(self):
		self.link_with_lead_contact_and_address()

	def on_trash(self):
		self.unlink_dynamic_links()

	def update_lead_details(self):
		for row in self.get('prospect_lead'):
			lead = frappe.get_value('Lead', row.lead, ['lead_name', 'status', 'email_id', 'mobile_no'], as_dict=True)
			row.lead_name = lead.lead_name
			row.status = lead.status
			row.email = lead.email_id
			row.mobile_no = lead.mobile_no

	def link_with_lead_contact_and_address(self):
		for row in self.prospect_lead:
			links = frappe.get_all('Dynamic Link', filters={'link_doctype': 'Lead', 'link_name': row.lead}, fields=['parent', 'parenttype'])
			for link in links:
				linked_doc = frappe.get_doc(link['parenttype'], link['parent'])
				exists = False

				for d in linked_doc.get('links'):
					if d.link_doctype == self.doctype and d.link_name == self.name:
						exists = True

				if not exists:
					linked_doc.append('links', {
						'link_doctype': self.doctype,
						'link_name': self.name
					})
					linked_doc.save(ignore_permissions=True)

	def unlink_dynamic_links(self):
		links = frappe.get_all('Dynamic Link', filters={'link_doctype': self.doctype, 'link_name': self.name}, fields=['parent', 'parenttype'])

		for link in links:
			linked_doc = frappe.get_doc(link['parenttype'], link['parent'])

			if len(linked_doc.get('links')) == 1:
				linked_doc.delete(ignore_permissions=True)
			else:
				to_remove = None
				for d in linked_doc.get('links'):
					if d.link_doctype == self.doctype and d.link_name == self.name:
						to_remove = d
				if to_remove:
					linked_doc.remove(to_remove)
					linked_doc.save(ignore_permissions=True)

@frappe.whitelist()
def make_customer(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.customer_type = "Company"
		target.company_name = source.name
		target.customer_group = source.customer_group or frappe.db.get_default("Customer Group")

	doclist = get_mapped_doc("Prospect", source_name,
		{"Prospect": {
			"doctype": "Customer",
			"field_map": {
				"company_name": "customer_name",
				"currency": "default_currency",
				"fax": "fax"
			}
		}}, target_doc, set_missing_values, ignore_permissions=False)

	return doclist

@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.opportunity_from = "Prospect"
		target.customer_name = source.company_name
		target.customer_group = source.customer_group or frappe.db.get_default("Customer Group")

	doclist = get_mapped_doc("Prospect", source_name,
		{"Prospect": {
			"doctype": "Opportunity",
			"field_map": {
				"name": "party_name",
			}
		}}, target_doc, set_missing_values, ignore_permissions=False)

	return doclist

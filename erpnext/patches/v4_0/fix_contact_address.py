from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("website", "doctype", "contact_us_settings")
	address = frappe.db.get_value("Contact Us Settings", None, "address")
	if address:
		address = frappe.get_doc("Address", address)
		contact = frappe.get_doc("Contact Us Settings", "Contact Us Settings")
		for f in ("address_title", "address_line1", "address_line2", "city", "state", "country", "pincode"):
			contact.set(f, address.get(f))
		
		contact.save()
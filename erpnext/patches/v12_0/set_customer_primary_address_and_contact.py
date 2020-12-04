import frappe
from frappe.contacts.doctype.address.address import get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from erpnext.selling.doctype.customer.customer import make_contact


def execute():
	frappe.reload_doc("selling", "doctype", "customer")
	frappe.reload_doc("contacts", "doctype", "address")
	frappe.reload_doc("contacts", "doctype", "contact")
	
	for d in frappe.get_all("Customer"):
		doc = frappe.get_doc("Customer", d.name)
		
		default_address_name = get_default_address("Customer", d.name)
		if default_address_name:
			default_address = frappe.get_doc("Address", default_address_name)
			if default_address.get('phone'):
				default_contact_name = get_default_contact("Customer", d.name)
				if default_contact_name:
					default_contact = frappe.get_doc("Contact", default_contact_name)
				else:
					default_contact = make_contact(doc)
					
				if not default_contact.phone_nos:
					default_contact.add_phone(default_address.get('phone'), is_primary_phone=1)
					default_contact.save()

		doc.update_primary_address()
		doc.update_primary_contact()

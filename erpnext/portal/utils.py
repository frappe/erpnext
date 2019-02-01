from __future__ import unicode_literals
import frappe

def set_default_role(doc, method):
	'''Set customer, supplier, student, guardian based on email'''
	if frappe.flags.setting_role or frappe.flags.in_migrate:
		return

	roles = frappe.get_roles(doc.name)

	contact_name = frappe.get_value('Contact', dict(email_id=doc.email))
	if contact_name:
		contact = frappe.get_doc('Contact', contact_name)
		for link in contact.links:
			frappe.flags.setting_role = True
			if link.link_doctype=='Customer' and 'Customer' not in roles:
				doc.add_roles('Customer')
			elif link.link_doctype=='Supplier' and 'Supplier' not in roles:
				doc.add_roles('Supplier')
	elif frappe.get_value('Student', dict(student_email_id=doc.email)) and 'Student' not in roles:
		doc.add_roles('Student')
	elif frappe.get_value('Guardian', dict(email_address=doc.email)) and 'Guardian' not in roles:
		doc.add_roles('Guardian')

import frappe

def set_default_role(doc, method):
	'''Set customer, supplier, student based on email'''
	if frappe.flags.setting_role or frappe.flags.in_migrate:
		return
	contact_name = frappe.get_value('Contact', dict(email_id=doc.email))
	if contact_name:
		contact = frappe.get_doc('Contact', contact_name)
		for link in contact.links:
			frappe.flags.setting_role = True
			if link.link_doctype=='Customer':
				doc.add_roles('Customer')
			elif link.link_doctype=='Supplier':
				doc.add_roles('Supplier')
	elif frappe.get_value('Student', dict(student_email_id=doc.email)):
		doc.add_roles('Student')

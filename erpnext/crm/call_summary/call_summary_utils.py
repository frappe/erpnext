import frappe

@frappe.whitelist()
def get_contact_doc(phone_number):
	contacts = frappe.get_all('Contact', filters={
		'phone': phone_number
	}, fields=['*'])

	if contacts:
		return contacts[0]
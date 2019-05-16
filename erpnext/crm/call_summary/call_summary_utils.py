import frappe

@frappe.whitelist()
def get_contact_doc(phone_number):
	phone_number = phone_number[-10:]
	contacts = frappe.get_all('Contact', or_filters={
		'phone': ['like', '%{}%'.format(phone_number)],
		'mobile_no': ['like', '%{}%'.format(phone_number)]
	}, fields=['*'])

	if contacts:
		return contacts[0]
import frappe

@frappe.whitelist()
def get_contact_doc(phone_number):
	phone_number = phone_number[-10:]
	contacts = frappe.get_all('Contact', or_filters={
		'phone': ['like', '%{}'.format(phone_number)],
		'mobile_no': ['like', '%{}'.format(phone_number)]
	}, fields=['*'])

	if contacts:
		return contacts[0]

@frappe.whitelist()
def get_last_communication(phone_number, customer=None):
	# find last communication through phone_number
	# find last issues, opportunity, lead
	pass
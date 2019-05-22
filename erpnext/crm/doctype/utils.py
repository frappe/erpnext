import frappe

@frappe.whitelist()
def get_document_with_phone_number(number):
	# finds contacts and leads
	if not number: return
	number = number[-10:]
	number_filter = {
		'phone': ['like', '%{}'.format(number)],
		'mobile_no': ['like', '%{}'.format(number)]
	}
	contacts = frappe.get_all('Contact', or_filters=number_filter, limit=1)

	if contacts:
		return frappe.get_doc('Contact', contacts[0].name)

	leads = frappe.get_all('Lead', or_filters=number_filter, limit=1)

	if leads:
		return frappe.get_doc('Lead', leads[0].name)


def get_customer_last_interaction(contact_doc):
	#
	pass
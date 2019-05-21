import frappe

def get_document_with_phone_number(number):
	# finds contacts and leads
	number = number[-10:]
	number_filter = {
		'phone': ['like', '%{}'.format(number)],
		'mobile_no': ['like', '%{}'.format(number)]
	}
	contacts = frappe.get_all('Contact', or_filters=number_filter,
		fields=['name'], limit=1)

	if contacts:
		return frappe.get_doc('Contact', contacts[0].name)

	leads = frappe.get_all('Leads', or_filters=number_filter,
		fields=['name'], limit=1)

	if leads:
		return frappe.get_doc('Lead', leads[0].name)
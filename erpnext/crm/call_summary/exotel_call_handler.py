import frappe

@frappe.whitelist(allow_guest=True)
def handle_request(*args, **kwargs):
	# r = frappe.request

	# print(r.args.to_dict(), args, kwargs)

	incoming_phone_number = kwargs.get('CallFrom')
	contact = get_contact_doc(incoming_phone_number)
	last_communication = get_last_communication(incoming_phone_number, contact)

	data = {
		'contact': contact,
		'call_payload': kwargs,
		'last_communication': last_communication
	}

	frappe.publish_realtime('incoming_call', data)


def get_contact_doc(phone_number):
	phone_number = phone_number[-10:]
	number_filter = {
		'phone': ['like', '%{}'.format(phone_number)],
		'mobile_no': ['like', '%{}'.format(phone_number)]
	}
	contacts = frappe.get_all('Contact', or_filters=number_filter,
		fields=['name'], limit=1)

	if contacts:
		return frappe.get_doc('Contact', contacts[0].name)

	leads = frappe.get_all('Leads', or_filters=number_filter,
		fields=['name'], limit=1)

	if leads:
		return frappe.get_doc('Lead', leads[0].name)


def get_last_communication(phone_number, contact):
	# frappe.get_all('Communication', filter={})
	return {}

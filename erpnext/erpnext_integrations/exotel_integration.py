import frappe
from erpnext.crm.doctype.utils import get_document_with_phone_number

@frappe.whitelist(allow_guest=True)
def handle_incoming_call(*args, **kwargs):
	incoming_phone_number = kwargs.get('CallFrom')

	contact = get_document_with_phone_number(incoming_phone_number)
	last_communication = get_last_communication(incoming_phone_number, contact)
	call_log = create_call_log(kwargs)
	data = {
		'contact': contact,
		'call_payload': kwargs,
		'last_communication': last_communication,
		'call_log': call_log
	}

	frappe.publish_realtime('incoming_call', data)


def get_last_communication(phone_number, contact):
	# frappe.get_all('Communication', filter={})
	return {}

def create_call_log(call_payload):
	communication = frappe.new_doc('Communication')
	communication.subject = frappe._('Call from {}').format(call_payload.get("CallFrom"))
	communication.communication_medium = 'Phone'
	communication.send_email = 0
	communication.phone_no = call_payload.get("CallFrom")
	communication.comment_type = 'Info'
	communication.communication_type = 'Communication'
	communication.status = 'Open'
	communication.sent_or_received = 'Received'
	communication.content = 'call_payload'
	communication.communication_date = call_payload.get('StartTime')
	# communication.sid = call_payload.get('CallSid')
	# communication.exophone = call_payload.get('CallTo')
	# communication.call_receiver = call_payload.get('DialWhomNumber')
	communication.save(ignore_permissions=True)
	return communication

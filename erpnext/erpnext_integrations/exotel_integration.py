import frappe
from erpnext.crm.doctype.utils import get_document_with_phone_number
import requests

# api/method/erpnext.erpnext_integrations.exotel_integration.handle_incoming_call

@frappe.whitelist(allow_guest=True)
def handle_incoming_call(*args, **kwargs):
	# incoming_phone_number = kwargs.get('CallFrom')

	# contact = get_document_with_phone_number(incoming_phone_number)
	# last_communication = get_last_communication(incoming_phone_number, contact)
	call_log = create_call_log(kwargs)
	data = frappe._dict({
		'call_from': kwargs.get('CallFrom'),
		'agent_email': kwargs.get('AgentEmail'),
		'call_type': kwargs.get('Direction'),
		'call_log': call_log
	})

	frappe.publish_realtime('show_call_popup', data, user=data.agent_email)


def get_last_communication(phone_number, contact):
	# frappe.get_all('Communication', filter={})
	return {}

def create_call_log(call_payload):
	communication = frappe.get_all('Communication', {
		'communication_medium': 'Phone',
		'call_id': call_payload.get('CallSid'),
	}, limit=1)

	if communication:
		log = frappe.get_doc('Communication', communication[0].name)
		log.call_status = 'Connected'
		log.save(ignore_permissions=True)
		return log

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
	communication.call_status = 'Incoming'
	communication.communication_date = call_payload.get('StartTime')
	communication.call_id = call_payload.get('CallSid')
	communication.save(ignore_permissions=True)
	return communication

def get_call_status(call_id):
	settings = get_exotel_settings()
	response = requests.get('https://{api_key}:{api_token}@api.exotel.com/v1/Accounts/erpnext/{sid}/{call_id}.json'.format(
		api_key=settings.api_key,
		api_token=settings.api_token,
		call_id=call_id
	))
	return response.json()

@frappe.whitelist(allow_guest=True)
def make_a_call(from_number, to_number, caller_id):
	settings = get_exotel_settings()
	response = requests.post('https://{api_key}:{api_token}@api.exotel.com/v1/Accounts/{sid}/Calls/connect.json'.format(
		api_key=settings.api_key,
		api_token=settings.api_token,
	), data={
		'From': from_number,
		'To': to_number,
		'CallerId': caller_id
	})

	return response.json()

def get_exotel_settings():
	return frappe.get_single('Exotel Settings')
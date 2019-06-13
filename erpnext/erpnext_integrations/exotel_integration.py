import frappe
from erpnext.crm.doctype.utils import get_employee_emails_for_popup
import requests

# api/method/erpnext.erpnext_integrations.exotel_integration.handle_incoming_call
# api/method/erpnext.erpnext_integrations.exotel_integration.handle_end_call
# api/method/erpnext.erpnext_integrations.exotel_integration.handle_missed_call

@frappe.whitelist(allow_guest=True)
def handle_incoming_call(*args, **kwargs):
	exotel_settings = get_exotel_settings()
	if not exotel_settings.enabled: return

	status = kwargs.get('Status')

	if status == 'free':
		# call disconnected for agent
		# "and get_call_status(kwargs.get('CallSid')) in ['in-progress']" - additional check to ensure if the call was redirected
		return

	call_log = get_call_log(kwargs)

	employee_emails = get_employee_emails_for_popup(kwargs.get('To'))
	for email in employee_emails:
		frappe.publish_realtime('show_call_popup', call_log, user=email)

@frappe.whitelist(allow_guest=True)
def handle_end_call(*args, **kwargs):
	call_log = update_call_log(kwargs, 'Completed')
	frappe.publish_realtime('call_disconnected', call_log)

@frappe.whitelist(allow_guest=True)
def handle_missed_call(*args, **kwargs):
	call_log = update_call_log(kwargs, 'Missed')
	frappe.publish_realtime('call_disconnected', call_log)

def update_call_log(call_payload, status):
	call_log = get_call_log(call_payload, False)
	if call_log:
		call_log.status = status
		call_log.duration = call_payload.get('DialCallDuration') or 0
		call_log.save(ignore_permissions=True)
		frappe.db.commit()
		return call_log


def get_call_log(call_payload, create_new_if_not_found=True):
	call_log = frappe.get_all('Call Log', {
		'id': call_payload.get('CallSid'),
	}, limit=1)

	if call_log:
		return frappe.get_doc('Call Log', call_log[0].name)
	elif create_new_if_not_found:
		call_log = frappe.new_doc('Call Log')
		call_log.id = call_payload.get('CallSid')
		call_log.to = call_payload.get('To')
		call_log.status = 'Ringing'
		setattr(call_log, 'from', call_payload.get('CallFrom'))
		call_log.save(ignore_permissions=True)
		frappe.db.commit()
		return call_log

@frappe.whitelist()
def get_call_status(call_id):
	endpoint = get_exotel_endpoint('Calls/{call_id}.json'.format(call_id=call_id))
	response = requests.get(endpoint)
	status = response.json().get('Call', {}).get('Status')
	return status

@frappe.whitelist()
def make_a_call(from_number, to_number, caller_id):
	endpoint = get_exotel_endpoint('Calls/connect.json?details=true')
	response = requests.post(endpoint, data={
		'From': from_number,
		'To': to_number,
		'CallerId': caller_id
	})

	return response.json()

def get_exotel_settings():
	return frappe.get_single('Exotel Settings')

@frappe.whitelist(allow_guest=True)
def get_phone_numbers():
	numbers = 'some number'
	whitelist_numbers(numbers, 'for number')
	return numbers

def whitelist_numbers(numbers, caller_id):
	endpoint = get_exotel_endpoint('CustomerWhitelist')
	response = requests.post(endpoint, data={
		'VirtualNumber': caller_id,
		'Number': numbers,
	})

	return response

def get_all_exophones():
	endpoint = get_exotel_endpoint('IncomingPhoneNumbers')
	response = requests.post(endpoint)
	return response

def get_exotel_endpoint(action):
	settings = get_exotel_settings()
	return 'https://{api_key}:{api_token}@api.exotel.com/v1/Accounts/{sid}/{action}'.format(
		api_key=settings.api_key,
		api_token=settings.api_token,
		sid=settings.account_sid,
		action=action
	)
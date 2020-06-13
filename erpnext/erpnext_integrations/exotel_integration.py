import frappe
import requests
from frappe import _
from frappe.utils import cint

# Endpoints for webhook
#
# Incoming Call:
# <site>/api/method/erpnext.erpnext_integrations.exotel_integration.handle_incoming_call/<key>
# Outgoing Call:
#  <site>/api/method/erpnext.erpnext_integrations.exotel_integration.update_call_status/<key>

# Exotel Reference:
# https://developer.exotel.com/api/
# https://support.exotel.com/support/solutions/articles/48283-working-with-passthru-applet

@frappe.whitelist(allow_guest=True)
def handle_incoming_call(**kwargs):
	validate_request()
	try:
		if is_integration_enabled(): return

		call_payload = kwargs
		status = call_payload.get('Status')
		direction = call_payload.get('Direction')
		if status == 'free' or direction != 'incoming':
			return

		call_log = get_call_log(call_payload)
		if not call_log:
			create_call_log(
				call_id=call_payload.get('CallSid'),
				from_number=call_payload.get('CallFrom'),
				to_number=call_payload.get('CallTo'),
				medium=call_payload.get('To')
			)
		else:
			update_call_log(call_payload, call_log=call_log)
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(title="Error while creating incoming call record")
		frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def update_call_status(**kwargs):
	validate_request()
	call_id = kwargs.get('CallSid')
	status = kwargs.get('Status')
	status = frappe.unscrub(status)
	try:
		frappe.db.set_value('Call Log', call_id, {
			'status': status,
			'start_time': kwargs.get('StartTime'),
			'end_time': kwargs.get('EndTime'),
			'recording_url': kwargs.get('RecordingUrl'),
			'duration': kwargs.get('ConversationDuration') or 0
		})
	except Exception as e:
		frappe.log_error(title='Error while updating outgoing call status')

	frappe.db.commit()


@frappe.whitelist()
def get_call_status(call_id):
	endpoint = get_exotel_endpoint('Calls/{call_id}.json'.format(call_id=call_id))
	response = requests.get(endpoint)
	call_data = response.json().get('Call', {})
	status = call_data.get('Status')
	return status

@frappe.whitelist()
def make_a_call(to_number, caller_id=None, link_to_document=None):
	endpoint = get_exotel_endpoint('Calls/connect.json?details=true')
	cell_number = frappe.get_value('Employee', {
		'user_id': frappe.session.user
	}, 'cell_number')

	if not cell_number:
		frappe.throw('Cell number not set')

	try:
		response = requests.post(endpoint, data={
			'From': cell_number,
			'To': to_number,
			'CallerId': caller_id,
			'Record': 'true' if frappe.db.get_single_value('Exotel Settings', 'record_call', True) else 'false',
			'StatusCallback': get_status_updater_url(),
			'StatusCallbackEvents': ['terminal'],
		})
		response.raise_for_status()
	except requests.exceptions.HTTPError as e:
		exc = response.json().get('RestException')
		if exc:
			frappe.throw(exc.get('Message'), title=_('Invalid Input'))
	else:
		res = response.json()
		call_payload = res.get('Call', {})
		if link_to_document:
			link_to_document = json.loads(link_to_document)
		create_call_log(
			call_id=call_payload.get('Sid'),
			from_number=call_payload.get('From'),
			to_number=call_payload.get('To'),
			medium=call_payload.get('PhoneNumberSid'),
			call_type="Outgoing",
			link_to_document=link_to_document
		)

	return response.json()

@frappe.whitelist()
def get_all_exophones():
	endpoint = get_exotel_endpoint('IncomingPhoneNumbers.json')
	response = requests.get(endpoint)
	numbers = [phone.get('IncomingPhoneNumber', {}).get('PhoneNumber') \
		for phone in response.json().get('IncomingPhoneNumbers', [])]
	return numbers


def validate_request():
	# workaround security since exotel does not support request signature
	# /api/method/<exotel-integration-method>/<key>
	key = ''
	webhook_key = frappe.db.get_single_value('Exotel Settings', 'webhook_key')
	path = frappe.request.path[1:].split("/")
	if len(path) == 4 and path[3]:
		key = path[3]
	is_valid = key and key == webhook_key

	if not is_valid:
		frappe.throw(_('Unauthorized request'), exc=frappe.PermissionError)

def create_call_log(call_id, from_number, to_number, medium,
	status='Ringing', call_type='Incoming', link_to_document=None):
	call_log = frappe.new_doc('Call Log')
	call_log.id = call_id
	call_log.to = to_number
	call_log.medium = medium
	call_log.type = call_type
	call_log.status = status
	setattr(call_log, 'from', from_number)
	if link_to_document:
		call_log.append('links', link_to_document)
	call_log.save(ignore_permissions=True)
	frappe.db.commit()
	return call_log

def update_call_log(call_payload, status='Ringing', call_log=None):
	call_log = call_log or get_call_log(call_payload)
	status = call_payload.get('DialCallStatus')
	status = frappe.unscrub(status)
	try:
		if call_log:
			call_log.status = status
			# resetting this because call might be redirected to other number
			call_log.to = call_payload.get('DialWhomNumber')
			call_log.duration = call_payload.get('DialCallDuration') or 0
			call_log.recording_url = call_payload.get('RecordingUrl')
			call_log.start_time = call_payload.get('StartTime')
			call_log.end_time = call_payload.get('EndTime')
			call_log.save(ignore_permissions=True)
			frappe.db.commit()
			return call_log
	except Exception as e:
		frappe.log_error(title="Error while updating incoming call record")
		frappe.db.commit()

def get_call_log(call_payload):
	try:
		return frappe.get_doc('Call Log', call_payload.get('CallSid'))
	except frappe.DoesNotExistError:
		pass

def get_status_updater_url():
	from frappe.utils.data import get_url
	return get_url('api/method/erpnext.erpnext_integrations.exotel_integration.update_call_status/{key}')

def get_exotel_endpoint(action, version='v1'):
	api_key = frappe.db.get_single_value('Exotel Settings', 'api_key')
	api_token = frappe.db.get_single_value('Exotel Settings', 'api_token')
	account_sid = frappe.db.get_single_value('Exotel Settings', 'account_sid')

	return 'https://{api_key}:{api_token}@api.exotel.com/{version}/Accounts/{sid}/{action}'.format(
		version=version,
		api_key=api_key,
		api_token=api_token,
		sid=account_sid,
		action=action
	)

def is_integration_enabled():
	frappe.db.get_single_value('Exotel Settings', 'enabled', True)

def whitelist_numbers(numbers, caller_id):
	endpoint = get_exotel_endpoint('CustomerWhitelist')
	response = requests.post(endpoint, data={
		'VirtualNumber': caller_id,
		'Number': numbers,
	})
	return response
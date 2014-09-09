# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json

from frappe import _, throw, msgprint
from frappe.utils import cstr, nowdate

from frappe.model.document import Document

class SMSSettings(Document):
	pass

def validate_receiver_nos(receiver_list):
	validated_receiver_list = []
	for d in receiver_list:
		# remove invalid character
		for x in [' ', '+', '-', '(', ')']:
			d = d.replace(x, '')

		validated_receiver_list.append(d)

	if not validated_receiver_list:
		throw(_("Please enter valid mobile nos"))

	return validated_receiver_list


def get_sender_name():
	"returns name as SMS sender"
	sender_name = frappe.db.get_value('Global Defaults', None, 'sms_sender_name') or \
		'ERPNXT'
	if len(sender_name) > 6 and \
			frappe.db.get_default("country") == "India":
		throw("""As per TRAI rule, sender name must be exactly 6 characters.
			Kindly change sender name in Setup --> Global Defaults.
			Note: Hyphen, space, numeric digit, special characters are not allowed.""")
	return sender_name

@frappe.whitelist()
def get_contact_number(contact_name, value, key):
	"returns mobile number of the contact"
	number = frappe.db.sql("""select mobile_no, phone from tabContact where name=%s and %s=%s""" %
		('%s', key, '%s'), (contact_name, value))
	return number and (number[0][0] or number[0][1]) or ''

@frappe.whitelist()
def send_sms(receiver_list, msg, sender_name = ''):

	import json
	if isinstance(receiver_list, basestring):
		receiver_list = json.loads(receiver_list)
		if not isinstance(receiver_list, list):
			receiver_list = [receiver_list]

	receiver_list = validate_receiver_nos(receiver_list)

	arg = {
		'receiver_list' : receiver_list,
		'message'		: msg,
		'sender_name'	: sender_name or get_sender_name()
	}

	if frappe.db.get_value('SMS Settings', None, 'sms_gateway_url'):
		ret = send_via_gateway(arg)
		msgprint(ret)
	else:
		msgprint(_("Please Update SMS Settings"))

def send_via_gateway(arg):
	ss = frappe.get_doc('SMS Settings', 'SMS Settings')
	args = {ss.message_parameter : arg.get('message')}
	for d in ss.get("static_parameter_details"):
		args[d.parameter] = d.value

	resp = []
	for d in arg.get('receiver_list'):
		args[ss.receiver_parameter] = d
		resp.append(send_request(ss.sms_gateway_url, args))

	return resp

# Send Request
# =========================================================
def send_request(gateway_url, args):
	import httplib, urllib
	server, api_url = scrub_gateway_url(gateway_url)
	conn = httplib.HTTPConnection(server)  # open connection
	headers = {}
	headers['Accept'] = "text/plain, text/html, */*"
	conn.request('GET', api_url + urllib.urlencode(args), headers = headers)    # send request
	resp = conn.getresponse()     # get response
	resp = resp.read()
	return resp

# Split gateway url to server and api url
# =========================================================
def scrub_gateway_url(url):
	url = url.replace('http://', '').strip().split('/')
	server = url.pop(0)
	api_url = '/' + '/'.join(url)
	if not api_url.endswith('?'):
		api_url += '?'
	return server, api_url


# Create SMS Log
# =========================================================
def create_sms_log(arg, sent_sms):
	sl = frappe.get_doc('SMS Log')
	sl.sender_name = arg['sender_name']
	sl.sent_on = nowdate()
	sl.receiver_list = cstr(arg['receiver_list'])
	sl.message = arg['message']
	sl.no_of_requested_sms = len(arg['receiver_list'])
	sl.no_of_sent_sms = sent_sms
	sl.save()

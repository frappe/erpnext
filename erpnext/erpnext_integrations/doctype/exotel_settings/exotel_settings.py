# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.model.document import Document
from erpnext.crm.doctype.crm_settings.crm_settings import display_popup
from six.moves.urllib.parse import urlparse
import requests

class ExotelSettings(Document):
	def validate(self):
		self.validate_credentials()
		self.create_delete_custom_fields()

	def validate_credentials(self):
		if self.enable_integration:
			response = requests.get('https://api.exotel.com/v1/Accounts/{sid}'.format(sid = self.exotel_sid),
				auth=(self.exotel_sid, self.exotel_token))
			if(response.status_code != 200):
				frappe.throw(_("Invalid credentials. Please try again with valid credentials"))

	def create_delete_custom_fields(self):
		if self.enable_integration:
			# create
			create_custom_fields = False
			names = ["Communication-call_details","Communication-exophone","Communication-sid","Communication-recording_url"]

			for i in names:
				if not frappe.get_value("Custom Field",{"name":i}):
					create_custom_fields = True
					break;

			if create_custom_fields:
				labels = ["Call Details","Exophone","SID","Recording URL"]
				types = ["Section Break","Read Only","Read Only","Long Text"]

				insert_after = ["field_request","call_details","exophone","sid"]
				for index,i in enumerate(zip(labels,types)):
					custom = frappe.new_doc("Custom Field")
					custom.dt = "Communication"
					custom.label = i[0]
					custom.fieldtype = i[1]
					custom.insert_after = insert_after[index]
					custom.read_only = 1
					custom.save()

		elif not self.enable_integration:
			# delete
			names = ["Communication-call_details","Communication-exophone","Communication-sid","Communication-recording_url"]
			for name in names:
				frappe.delete_doc("Custom Field",name)

		frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def handle_incoming_call(*args, **kwargs):
	""" Handles incoming calls in telephony service. """
	r = frappe.request

	try:
		if args or kwargs:
			content = args or kwargs
			comm = frappe.new_doc("Communication")
			comm.subject = "Incoming Call " + frappe.utils.get_datetime_str(frappe.utils.get_datetime())
			comm.send_email = 0
			comm.communication_medium = "Phone"
			comm.phone_no = content.get("CallFrom")
			comm.comment_type = "Info"
			comm.communication_type = "Communication"
			comm.status = "Open"
			comm.sent_or_received = "Received"
			comm.content = "Incoming Call " + frappe.utils.get_datetime_str(frappe.utils.get_datetime()) + "<br>" + str(content)
			comm.communication_date = content.get("StartTime")
			comm.sid = content.get("CallSid")
			comm.exophone = content.get("CallTo")
			comm.call_receiver = content.get("DialWhomNumber")

			comm.save(ignore_permissions=True)
			frappe.db.commit()

			# data sent to crm-dashboard
			message = {
				"communication_name":comm.name,
				"communication_phone_no":comm.phone_no,
				"call_receiver":comm.call_receiver,
				"communication_exophone":comm.exophone,
				"communication_reference_doctype":comm.reference_doctype or "",
				"communication_reference_name":comm.reference_name or ""
			}

			if(frappe.get_doc("CRM Settings").show_popup_for_incoming_calls):
				display_popup(content.get("CallFrom"), message)

			# to refresh crm-dashboard in realtime 
			frappe.publish_realtime('new_call', message, after_commit=False)

			return comm
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Error log for incoming call")

@frappe.whitelist(allow_guest=True)
def capture_call_details(*args, **kwargs):
	""" Captures post-call details in telephony service. """

	try:
		if args or kwargs:
			credentials = frappe.get_doc("Exotel Settings")
			content = args or kwargs

			response = requests.get('https://api.exotel.com/v1/Accounts/{sid}/Calls/{callsid}.json'.format(sid = credentials.exotel_sid,callsid = content.get("CallSid")),\
				auth=(credentials.exotel_sid,credentials.exotel_token))

			content = response.json()["Call"]

			if response.status_code == 200:
				call = frappe.get_all("Communication", filters={"sid":content.get("CallSid")}, fields=["name"])
				comm = frappe.get_doc("Communication",call[0].name)
				comm.recording_url = content.get("RecordingUrl")
				comm.save(ignore_permissions=True)
				frappe.db.commit()
				return comm
			else:
				frappe.msgprint(_("Authenication error. Invalid exotel credentials."))
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Error in capturing call details")

@frappe.whitelist()
def handle_outgoing_call(To, CallerId,reference_doctype,reference_name):
	"""Handles outgoing calls in telephony service.

	:param From: Number of user
	:param To: Number of customer
	:param CallerId: Exophone number
	:param reference_doctype: links reference doctype,if any
	:param reference_name: links reference docname,if any

	"""
	r = frappe.request
	try:
		credentials = frappe.get_doc("Exotel Settings")
		
		endpoint = "/api/method/frappe.integrations.doctype.exotel_settings.exotel_settings.capture_call_details"
		url = frappe.request.url

		server_url = '{uri.scheme}://{uri.netloc}'.format(
			uri=urlparse(url)
		)
		status_callback_url = server_url + endpoint

		response = requests.post('https://api.exotel.in/v1/Accounts/{sid}/Calls/connect.json'.format(sid=credentials.exotel_sid),
        auth = (credentials.exotel_sid,credentials.exotel_token),
		data = {
			'From': frappe.get_doc("User",frappe.session.user).phone or frappe.get_doc("User",frappe.session.user).mobile_no,
			'To': To,
			'CallerId': CallerId,
			'StatusCallback': status_callback_url
		})

		if response.status_code == 200:
			content = response.json()["Call"]

			comm = frappe.new_doc("Communication")
			comm.subject = "Outgoing Call " + frappe.utils.get_datetime_str(frappe.utils.get_datetime())
			comm.send_email = 0
			comm.communication_medium = "Phone"
			comm.phone_no = content.get("To")
			comm.comment_type = "Info"
			comm.communication_type = "Communication"
			comm.status = "Open"
			comm.sent_or_received = "Sent"
			comm.content = "Outgoing Call " + frappe.utils.get_datetime_str(frappe.utils.get_datetime()) + "<br>" + str(content)
			comm.communication_date = content.get("StartTime")
			comm.recording_url = content.get("RecordingUrl")
			comm.sid = content.get("Sid")
			comm.reference_doctype = reference_doctype
			comm.reference_name = reference_name

			comm.save(ignore_permissions=True)
			frappe.db.commit()

			return comm
		else:
			frappe.msgprint(_("Authenication error. Invalid exotel credentials."))
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Error log for outgoing call")
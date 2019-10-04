# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.print_format import download_pdf
from frappe.model.document import Document
from frappe.core.doctype.sms_settings.sms_settings import validate_receiver_nos
from twilio.rest import Client
from six import string_types


class WhatsappSettings(Document):
	def validate(self):
		validate_receiver_nos([self.wp_number])


@frappe.whitelist(allow_guest=True)
def get_pdf_for_whatsapp(doctype, name, key):
	doc = frappe.get_doc(doctype, name)
	if not key == doc.get_signature():
		return 403
	download_pdf(doctype, name, format=None, doc=None, no_letterhead=0)


def get_url_for_whatsapp(doctype, name):
	doc = frappe.get_doc(doctype, name)
	return "{url}/api/method/erpnext.erpnext_integrations.doctype.whatsapp_settings.whatsapp_settings.get_pdf_for_whatsapp?doctype={doctype}&name={name}&key={key}".format(
		url=frappe.utils.get_url(),
		doctype=doctype,
		name=name,
		key=doc.get_signature()
	).replace(" ", "%20")


@frappe.whitelist()
def send_whatsapp(receiver_list, msg, doctype="", name=""):
	import json
	if isinstance(receiver_list, string_types):
		receiver_list = json.loads(receiver_list)
		if not isinstance(receiver_list, list):
			receiver_list = [receiver_list]

	receiver_list = validate_receiver_nos(receiver_list)

	wp_settings = frappe.get_doc("Whatsapp Settings")
	client = Client(wp_settings.twilio_sid, wp_settings.twilio_token)
	errors = []

	message_kwargs = {
		"from_": 'whatsapp:{}'.format(wp_settings.wp_number),
		"body": msg
	}

	attachment_kwargs = {}
	if doctype:
		attachment_kwargs = {
			"from_": 'whatsapp:{}'.format(wp_settings.wp_number),
			"media_url": get_url_for_whatsapp(doctype, name),
			"body": "{name}.pdf".format(name=name)
		}

	for rec in receiver_list:
		if attachment_kwargs:
			attachment_kwargs.update({"to": 'whatsapp:{}'.format(rec)})
			resp = _send_whatsapp(attachment_kwargs, client)
			if not resp:
				errors.append(rec)
				continue

		if not msg:
			continue

		message_kwargs.update({"to": 'whatsapp:{}'.format(rec)})
		resp = _send_whatsapp(message_kwargs, client)
		if not resp:
			errors.append(rec)

	if errors:
		frappe.msgprint(_("The message wasn't correctly delivered to: {}".format(", ".join(errors))))


def _send_whatsapp(message_dict, client):
	response = client.messages.create(**message_dict)
	return response.sid

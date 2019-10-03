# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.core.doctype.sms_settings.sms_settings import validate_receiver_nos
from twilio.rest import Client
from six import string_types
from frappe.utils.file_manager import upload, remove_file_by_url
import base64


class WhatsappSettings(Document):
    def validate(self):
        validate_receiver_nos([self.wp_number])


def prepare_file_for_whatsapp(filename, filecontent):
    frappe.form_dict.filename = filename
    frappe.form_dict.is_private = 0
    frappe.form_dict.filedata = base64.b64encode(filecontent)
    return upload()


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

    attachment = None
    if doctype:
        filecontent = frappe.get_print(doctype, name, None, doc=None, no_letterhead=1, as_pdf=1)
        filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
        attachment = prepare_file_for_whatsapp(filename, filecontent)
        message_kwargs.update({"MediaUrl": frappe.utils.get_url() + file.get("file_url", "")[1:]})

    for rec in receiver_list:
        message_kwargs.update({"to": 'whatsapp:{}'.format(rec)})
        response = client.messages.create(**message_kwargs)
        if not response.sid:
            errors.append(rec)

    if errors:
        frappe.msgprint(_("The message wasn't correctly delivered to: {}".format(", ".join(errors))))

    if attachment and response.status == "sent":
        remove_file_by_url(file.get("file_url", ""))

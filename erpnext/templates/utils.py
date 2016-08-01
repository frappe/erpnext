# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, json
from frappe import _
from frappe.utils import cint, formatdate

@frappe.whitelist(allow_guest=True)
def send_message(subject="Website Query", message="", sender="", status="Open"):
	from frappe.www.contact import send_message as website_send_message

	website_send_message(subject, message, sender)

	comm = frappe.get_doc({
		"doctype":"Communication",
		"subject": subject,
		"content": message,
		"sender": sender,
		"sent_or_received": "Received"
	})
	comm.insert(ignore_permissions=True)

	return "okay"

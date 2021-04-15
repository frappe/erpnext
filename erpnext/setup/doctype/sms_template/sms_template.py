# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.core.doctype.sms_settings.sms_settings import get_contact_number
from frappe.utils import cstr

class SMSTemplate(Document):
	def autoname(self):
		self.name = self.reference_doctype
		if self.type:
			self.name += "-" + self.type


@frappe.whitelist()
def get_sms_defaults(dt, dn, type=None, contact=None, mobile_no=None, party_doctype=None, party_name=None):
	if not mobile_no and (contact or party_doctype or party_name):
		mobile_no = get_contact_number(contact, party_doctype, party_name)

	type = cstr(type)

	template = frappe.db.sql_list("""
		select message
		from `tabSMS Template`
		where reference_doctype = %s and ifnull(type, '') = %s
		limit 1
	""", [dt, type])
	template = template[0] if template else ""

	message = ""
	if template:
		doc = frappe.get_doc(dt, dn)
		context = {"doc": doc}
		message = frappe.render_template(template, context)

	return {
		"mobile_no": mobile_no,
		"message": message
	}

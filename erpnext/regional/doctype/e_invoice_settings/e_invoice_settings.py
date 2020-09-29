# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.data import cstr
from frappe.model.document import Document
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

class EInvoiceSettings(Document):
	def validate(self):
		mandatory_fields = ['client_id', 'client_secret', 'gstin', 'username', 'password', 'public_key']
		for d in mandatory_fields:
			if not self.get(d):
				frappe.throw(_("{} is required").format(frappe.unscrub(d)), title=_("Missing Values"))
	
	def before_save(self):
		if not self.public_key or self.has_value_changed('public_key_file'):
			self.public_key = self.read_key_file()

		make_property_setter("Sales Invoice", "irn", "reqd", self.enable, "Data")

	def read_key_file(self):
		key_file = frappe.get_doc('File', dict(attached_to_name=self.doctype, attached_to_field='public_key_file'))
		with open(key_file.get_full_path(), 'rb') as f:
			return cstr(f.read())
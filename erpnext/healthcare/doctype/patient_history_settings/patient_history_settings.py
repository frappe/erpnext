# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class PatientHistorySettings(Document):
	def validate(self):
		self.validate_date_fieldnames()

	def validate_date_fieldnames(self):
		for entry in self.custom_doctypes:
			field = frappe.get_meta(entry.document_type).get_field(entry.date_fieldname)
			if not field:
				frappe.throw(_('Row #{0}: No such Field named {1} found in the Document Type {2}.').format(
					entry.idx, frappe.bold(entry.date_fieldname), frappe.bold(entry.document_type)))

			if field.fieldtype not in ['Date', 'Datetime']:
				frappe.throw(_('Row #{0}: Field {1} in Document Type {2} is not a Date / Datetime field.').format(
					entry.idx, frappe.bold(entry.date_fieldname), frappe.bold(entry.document_type)))
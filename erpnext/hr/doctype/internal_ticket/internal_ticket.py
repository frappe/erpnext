# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

class InternalTicket(Document):

	def validate(self):
		if not self.raised_by:
			self.raised_by = frappe.session.user

@frappe.whitelist()
def make_task(source_name, target_doc=None):
	print(target_doc)
	return get_mapped_doc("Employee Issue", source_name, {
		"Employee Issue": {
			"doctype": 'Task',
			"field_map": {
				'name': "reference_docname",
				'doctype': "reference_doctype"
			},
		}
	}, target_doc)
# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.crm.doctype.utils import get_employee_emails_for_popup

class CallLog(Document):
	def after_insert(self):
		employee_emails = get_employee_emails_for_popup(self.medium)
		for email in employee_emails:
			frappe.publish_realtime('show_call_popup', self, user=email)

	def on_update(self):
		doc_before_save = self.get_doc_before_save()
		if doc_before_save and doc_before_save.status in ['Ringing'] and self.status in ['Missed', 'Completed']:
			frappe.publish_realtime('call_{id}_disconnected'.format(id=self.id), self)

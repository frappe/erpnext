# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Call(Document):
	def on_update(self):
		self.sync_communication()

	def sync_communication(self):
		if self.reference_doctype and self.reference_document:
			if frappe.db.exists("Communication", dict(reference_doctype=self.doctype, reference_name=self.name)):
				communication = frappe.get_doc("Communication", dict(reference_doctype=self.doctype, reference_name=self.name))
				self.update_communication(communication)
			else:
				self.create_communication()

	def create_communication(self):
			communication = frappe.new_doc("Communication")
			self.update_communication(communication)
			self.communication = communication.name

	def update_communication(self, communication):
		communication.communication_medium = "Phone"
		communication.subject = self.subject
		communication.content = self.description
		communication.communication_date = self.start_datetime
		communication.timeline_doctype = self.reference_doctype
		communication.timeline_name = self.reference_document
		communication.reference_doctype = self.doctype
		communication.reference_name = self.name
		communication.status = "Linked"
		communication.save()
		
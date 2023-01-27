# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class CustomerFeedback(Document):
	def validate(self):
		self.set_title()
		self.set_status()

	def set_title(self):
		self.title = self.customer_name or self.customer

	def set_status(self):
		if self.customer_feedback:
			self.status = "Completed"
		else:
			self.status = "Pending"

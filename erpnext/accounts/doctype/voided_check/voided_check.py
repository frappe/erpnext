# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class VoidedCheck(Document):
	def validate(self):		
		if self.docstatus == 0:
			if self.created_by == None:
				self.created_by = frappe.session.user

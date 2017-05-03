# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class IPSettings(Document):
	def validate(self):
		if self.drug_task:
			if not self.service_type:
				frappe.throw("Please select a Service Type")

# -*- coding: utf-8 -*-
# Copyright (c) 2020, earthians and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class HealthcareServiceOrder(Document):
	def validate(self):
		self.title = f'{self.patient_name} - {self.order}'

	def before_submit(self):
		if self.status != 'Active':
			self.status = 'Active'

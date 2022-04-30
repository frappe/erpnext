# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document
from erpnext.vehicles.vehicle_checklist import get_default_vehicle_checklist_items, set_missing_checklist

class ProjectTemplateCategory(Document):
	def onload(self):
		self.set_onload('default_customer_request_checklist_items', get_default_vehicle_checklist_items('customer_request_checklist'))
		self.set_missing_checklist()

	def validate(self):
		self.set_missing_checklist()

	def set_missing_checklist(self):
		if self.meta.has_field('customer_request_checklist'):
			set_missing_checklist(self, 'customer_request_checklist')

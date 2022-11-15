# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from erpnext.vehicles.vehicle_checklist import get_default_vehicle_checklist_items, set_updated_checklist

class ProjectTemplateCategory(Document):
	def onload(self):
		self.set_onload('default_customer_request_checklist_items', get_default_vehicle_checklist_items('customer_request_checklist'))
		self.set_updated_checklist()

	def set_updated_checklist(self):
		if self.meta.has_field('customer_request_checklist'):
			set_updated_checklist(self, 'customer_request_checklist')

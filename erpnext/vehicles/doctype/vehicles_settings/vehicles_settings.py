# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.vehicles.vehicle_checklist import validate_duplicate_checklist_items
from frappe.model.document import Document


class VehiclesSettings(Document):
	def validate(self):
		validate_duplicate_checklist_items(self.vehicle_checklist)
		validate_duplicate_checklist_items(self.customer_request_checklist)

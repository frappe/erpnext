# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document


class VehiclePanel(Document):
	def validate(self):
		self.validate_qty()

	def validate_qty(self):
		if flt(self.default_qty) < 0:
			frappe.throw(_("Default Qty cannot be negative"))

# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TaxWithholdingCategory(Document):
	def validate(self):
		if not frappe.db.get_value("Tax Withholding Category",
			{"is_default": 1, "name": ("!=", self.name)}, "name"):
			self.is_default = 1
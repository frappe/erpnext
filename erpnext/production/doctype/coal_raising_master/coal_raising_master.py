# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CoalRaisingMaster(Document):
	def validate(self):
		self.validate_field()
	def validate_field(self):
		if self.from_date > self.to_date:
			frappe.throw("From date cannot be before than to date")

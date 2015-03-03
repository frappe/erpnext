# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Operation(Document):
	def calculate_op_cost(self):
		if self.hour_rate and self.time_in_mins:
			self.operating_cost = flt(self.hour_rate) * flt(self.time_in_mins) / 60.0
		else :
			self.operating_cost = 0


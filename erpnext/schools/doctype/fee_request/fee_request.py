# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class FeeRequest(Document):
	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		self.total_amount = 0
		for d in self.components:
			self.total_amount += d.amount
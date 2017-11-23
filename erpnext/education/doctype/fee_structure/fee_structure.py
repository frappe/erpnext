# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class FeeStructure(Document):
	def validate(self):
		self.calculate_total()
		
	def calculate_total(self):
		"""Calculates total amount."""
		self.total_amount = 0
		for d in self.components:
			self.total_amount += d.amount
	

@frappe.whitelist()
def make_fee_schedule(source_name, target_doc=None):
	return get_mapped_doc("Fee Structure", source_name,	{
		"Fee Structure": {
			"doctype": "Fee Schedule",
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Fee Component": {
			"doctype": "Fee Component"
		}
	}, target_doc)
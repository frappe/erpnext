# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		self.validate_mandatory()
		self.cleanup_fields_value()
		
	def validate_mandatory(self):
		for field in ["apply_on", "applicable_for", "price_or_discount"]:
			val = self.doc.fields.get("applicable_for")
			if val and not self.doc.fields.get(frappe.scrub(val)):
				throw("{fname} {msg}".format(fname = _(val), msg = _(" is mandatory")), 
					frappe.MandatoryError)
		
	def cleanup_fields_value(self):
		fields = ["item_code", "item_group", "brand", "customer", "customer_group", 
			"territory", "supplier", "supplier_type", "campaign", "sales_partner", 
			"price", "discount_percentage"]
			
		for field_with_value in ["apply_on", "applicable_for", "price_or_discount"]:
			val = self.doc.fields.get(field_with_value)
			if val:
				fields.remove(frappe.scrub(val))
			
		for field in fields:
			self.doc.fields[field] = None
		
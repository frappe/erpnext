# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, throw
from frappe.model.document import Document

class CustomerRetention(Document):
	def validate(self):
		self.calculate_percentage_and_references()
		if self.docstatus == 1:
			self.calculate_retention()
			self.update_accounts_status()

	def calculate_percentage_and_references(self):
		if self.get("reasons"):
			total_percentage = 0
			for item in self.get("reasons"):
				total_percentage += item.percentage
			self.percentage_total = total_percentage
		if self.get("references"):
			total_references = 0
			withheld = 0
			for item in self.get("references"):
				total_references += item.net_total
				withheld += item.net_total * (self.percentage_total/100)
			self.total_references = total_references
			self.total_withheld = withheld
	
	def calculate_retention(self):
		for document in self.get("references"):
			total = document.net_total * (self.percentage_total/100)
			sales_invoice = frappe.get_doc("Sales Invoice", document.reference_name)
			sales_invoice.outstanding_amount -= total
			sales_invoice.save()
	
	def update_accounts_status(self):
		customer = frappe.get_doc("Customer", self.customer)
		if customer:
			customer.credit += self.total_withheld
			customer.remaining_balance -= self.total_withheld
			customer.save()


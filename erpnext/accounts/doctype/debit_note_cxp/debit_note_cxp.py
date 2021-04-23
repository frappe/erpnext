# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, throw
from frappe.model.document import Document

class DebitNoteCXP(Document):
	def validate(self):
		self.verificate_references_and_amount()
		self.calculate_total()
		if self.docstatus == 1:
			self.verificate_amount()

	def calculate_total(self):
		total_reference = 0
		for d in self.get("references"):
			total_reference += d.total_amount
			self.total_references = total_reference

		if self.tax_base != None:
			self.calculate_isv()
	
	def calculate_isv(self):
		item_tax_template = frappe.get_all("Item Tax Template", ["name"], filters = {"name": self.tax_template})
		for tax_template in item_tax_template:
			tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate"], filters = {"parent": tax_template.name})
			for tax in tax_details:
				tx_base = self.tax_base * (tax.tax_rate/100)
				self.isv = tx_base

	def verificate_references_and_amount(self):
		if len(self.get("references")) > 1:
			order_by = sorted(self.references, key=lambda item: item.total_amount)
			remaining_amount = self.amount
			for d in order_by:
				if remaining_amount <= d.total_amount:
					result = d.total_amount - remaining_amount
					if result <= 0:
						frappe.throw(_("The amount can not be accepted to pay the bills, the amount must pay the bills or pay one and advance another."))

	def verificate_amount(self):
		remaining = 0
		amount_total = self.amount
		if len(self.get("references")) > 1:
			for d in sorted(self.references, key=lambda item: item.total_amount):
				purchase_invoice = frappe.get_doc("Purchase Invoice", d.reference_name)
				if amount_total > d.total_amount:
					amount_total -= d.total_amount
					purchase_invoice.outstanding_amount -= d.total_amount
				else:
					if amount_total <= d.total_amount:
						purchase_invoice.outstanding_amount -= amount_total
				purchase_invoice.save()
		else: 
			for x in self.get("references"):
				if amount_total <= x.total_amount:
					purchase_invoice = frappe.get_doc("Purchase Invoice", x.reference_name)
					purchase_invoice.outstanding_amount -= self.amount
				purchase_invoice.save()
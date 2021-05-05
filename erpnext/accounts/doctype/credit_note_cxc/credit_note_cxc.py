# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, throw
from frappe.utils import getdate, nowdate, flt
from frappe.model.document import Document
from datetime import datetime, timedelta, date
from frappe.model.naming import parse_naming_series

class CreditNoteCXC(Document):
	def validate(self):
		self.calculate_total()
		self.validate_status()
		self.set_status()
		
	def on_load(self):
		self.validate_status()

	def calculate_total(self):
		total_base = 0			
		for taxes_list in self.get("taxes"):
			total_base += taxes_list.base_isv
			if total_base > self.amount:
				frappe.throw(_("Base tax cannot be greater than the amount"))
		if len(self.get("taxes")) > 0:	
			self.calculate_isv()
			total_taxes = self.isv_15 + self.isv_18
			total = self.amount + total_taxes
			self.document_balance = total
			self.outstanding_amount = total
		else:
			self.document_balance = self.amount
			self.outstanding_amount = self.amount
	
	def calculate_isv(self):
		for taxes_list in self.get("taxes"):
			item_tax_template = frappe.get_all("Item Tax Template", ["name"], filters = {"name": taxes_list.isv})
			for tax_template in item_tax_template:
				tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate"], filters = {"parent": tax_template.name})
				for tax in tax_details:
					if tax.tax_rate == 15:
						tx_base = taxes_list.base_isv * (tax.tax_rate/100)
						self.isv_15 = tx_base
					elif tax.tax_rate == 18:
						tx_base = taxes_list.base_isv * (tax.tax_rate/100)
						self.isv_18 = tx_base

	def validate_status(self):
		if self.outstanding_amount > 0:
			self.status = "Unpaid"
		elif  getdate(self.due_date) >= getdate(nowdate()):
			self.status = "Overdue"
		elif self.outstanding_amount <= 0:
			self.status = "Paid"
	
	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if flt(self.outstanding_amount) > 0 and getdate(self.due_date) < getdate(nowdate()):
					self.status = "Overdue"
				elif flt(self.outstanding_amount) > 0 and getdate(self.due_date) >= getdate(nowdate()):
					self.status = "Unpaid"
				elif flt(self.outstanding_amount)<=0:
					self.status = "Paid"
				else:
					self.status = "Submitted"
			else:
				self.status = "Draft"

		if update:
			self.db_set('status', self.status, update_modified = update_modified)

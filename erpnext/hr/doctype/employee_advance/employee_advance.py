# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

class EmployeeAdvanceOverPayment(frappe.ValidationError):
	pass

class EmployeeAdvance(Document):
	def validate(self):
		self.set_status()
	
	def set_status(self):
		self.status = {
			"0": "Draft",
			"1": "Submitted",
			"2": "Cancelled"
		}[cstr(self.docstatus or 0)]
		
		
	def set_total_advance_paid(self):
		paid_amount = frappe.db.sql("""
			select sum(debit_in_account_currency)
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
		""", (self.name, self.employee))[0][0]
		
		if paid_amount > self.advance_amount:
			frappe.throw(_("Payment Amount cannot be greater than advance amount"), 
				EmployeeAdvanceOverPayment)
		
		self.db_set("paid_amount", paid_amount)
		
		
		
		
		
		
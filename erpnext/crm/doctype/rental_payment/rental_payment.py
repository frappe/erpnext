# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, get_datetime, get_url, nowdate, now_datetime, money_in_words
from erpnext.accounts.general_ledger import make_gl_entries
from frappe import _
from erpnext.controllers.accounts_controller import AccountsController
# from erpnext.custom_utils import check_future_date

class RentalPayment(Document):	
	
	def on_submit(self):
		self.post_gl_entry()
		#self.consume_budget()
	
	def on_cancel(self):
		self.post_gl_entry()
		#self.cancel_budget_entry()

	def post_gl_entry(self):
		gl_entries = []
		if self.company == "Bank Of Bhutan":
			gl_entries.append(
				self.get_gl_dict({
						"account": self.debit_account,
						"debit": self.total,
						"debit_in_account_currency": self.total,
						"voucher_no": self.name,
						"voucher_type": self.doctype,
						"cost_center": self.cost_center,					
						"company": self.company,
						"remarks": self.remarks,
						"business_activity": self.business_activity,
					})
				)
			gl_entries.append(
				self.get_gl_dict({
						"account": self.credit_account,
						"credit": self.total,
						"credit_in_account_currency": self.total,
						"voucher_no": self.name,
						"voucher_type": self.doctype,
						"cost_center": self.cost_center,
						"company": self.company,
						"remarks": self.remarks,
						"business_activity": self.business_activity,
					})
				)
		make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=False)


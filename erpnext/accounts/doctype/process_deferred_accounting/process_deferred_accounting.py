# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.accounts.deferred_revenue import convert_deferred_expense_to_expense, \
	convert_deferred_revenue_to_income, build_conditions

class ProcessDeferredAccounting(Document):
	def validate(self):
		if self.end_date < self.start_date:
			frappe.throw(_("End date cannot be before start date"))

	def on_submit(self):
		conditions = build_conditions(self.type, self.account, self.company)
		if self.type == 'Income':
			convert_deferred_revenue_to_income(self.name, self.start_date, self.end_date, conditions)
		else:
			convert_deferred_expense_to_expense(self.name, self.start_date, self.end_date, conditions)

	def on_cancel(self):
		self.ignore_linked_doctypes = ['GL Entry']
		gl_entries = frappe.get_all('GL Entry', fields = ['*'],
			filters={
				'against_voucher_type': self.doctype,
				'against_voucher': self.name
			})

		make_reverse_gl_entries(gl_entries=gl_entries)
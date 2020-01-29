# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.deferred_revenue import convert_deferred_expense_to_expense, \
	convert_deferred_revenue_to_income

class ProcessDeferredAccounting(Document):
	def validate(self):
		if self.end_date < self.start_date:
			frappe.throw(_("End date cannot be before start date"))

	def on_submit(self):
		conditions = self.build_conditions()
		if self.type == 'Income':
			convert_deferred_revenue_to_income(self.name, self.start_date, self.end_date, conditions)
		else:
			convert_deferred_expense_to_expense(self.name, self.start_date, self.end_date, conditions)

	def on_cancel(self):
		frappe.db.sql("DELETE from `tabGL Entry` where against_voucher = %s", (self.name))

	def build_conditions(self):
		conditions=''
		deferred_account = "item.deferred_revenue_account" if self.type=="Income" else "item.deferred_expense_account"

		if self.account:
			conditions += "AND %s='%s'"%(deferred_account, self.account)
		elif self.company:
			conditions += "AND p.company='%s'"%(self.company)

		return conditions
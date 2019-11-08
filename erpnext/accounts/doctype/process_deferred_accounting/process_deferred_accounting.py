# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.deferred_revenue import convert_deferred_expense_to_expense, \
	convert_deferred_revenue_to_income

class ProcessDeferredAccounting(Document):
	def on_submit(self):
		conditions = self.build_conditions()
		if self.type == 'Income':
			convert_deferred_revenue_to_income(self.start_date, self.end_date, conditions)
		else:
			convert_deferred_expense_to_expense(self.start_date, self.end_date, conditions)

	def build_conditions(self):
		conditions=''
		if self.account:
			conditions += "AND item.deferred_revenue_account='%s'"%(self.account)
		elif self.company:
			conditions += "AND p.company='%s'"%(self.company)

		return conditions

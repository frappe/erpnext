# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import AccountsController
from frappe.utils import flt, comma_or, nowdate


class FinancialCustodyEntry(AccountsController):
	def validate(self):
		self.validate_gl()
		
	def validate_gl(self):
		financial_custody_account = self.get("financial_custody_account")
		if financial_custody_account:
			for row in financial_custody_account:
				if not row.referance:
					if row.debit >0 and row.credit>0:
						frappe.throw("Row must be cridit or debit not both")
				self.make_gl_entries(row)


	def make_gl_entries(self,d, cancel=0, adv_adj=0):
		from erpnext.accounts.general_ledger import make_gl_entries

		gl_map = []
		if d.debit or d.credit:
			gl_map.append(
				self.get_gl_dict({
					"account": d.account,
					"party_type": "Employee",
					"party": self.employee,
					"against": d.against,
					"debit": flt(d.debit, d.precision("debit")),
					"credit": flt(d.credit, d.precision("credit")),
					"debit_in_account_currency": flt(d.debit, d.precision("debit")),
					"credit_in_account_currency": flt(d.debit, d.precision("debit")),
					"against_voucher_type": "Financial Custody Entry",
					"against_voucher": self.name,
					"cost_center": self.cost_center,
					"project": self.project
				})
			)

		if gl_map:
			make_gl_entries(gl_map, cancel=cancel, adv_adj=adv_adj)

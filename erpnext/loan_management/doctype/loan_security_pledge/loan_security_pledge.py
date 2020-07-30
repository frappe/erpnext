# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import now_datetime, cint
from frappe.model.document import Document
from erpnext.loan_management.doctype.loan_security_shortfall.loan_security_shortfall import update_shortfall_status
from erpnext.loan_management.doctype.loan_security_price.loan_security_price import get_loan_security_price

class LoanSecurityPledge(Document):
	def validate(self):
		self.set_pledge_amount()
		self.validate_duplicate_securities()

	def on_submit(self):
		if self.loan:
			self.db_set("status", "Pledged")
			self.db_set("pledge_time", now_datetime())
			update_shortfall_status(self.loan, self.total_security_value)
			update_loan(self.loan, self.maximum_loan_value)

	def validate_duplicate_securities(self):
		security_list = []
		for security in self.securities:
			if security.loan_security not in security_list:
				security_list.append(security.loan_security)
			else:
				frappe.throw(_('Loan Security {0} added multiple times').format(frappe.bold(
					security.loan_security)))

	def set_pledge_amount(self):
		total_security_value = 0
		maximum_loan_value = 0

		for pledge in self.securities:

			if not pledge.qty and not pledge.amount:
				frappe.throw(_("Qty or Amount is mandatory for loan security!"))

			if not (self.loan_application and pledge.loan_security_price):
				pledge.loan_security_price = get_loan_security_price(pledge.loan_security)

			if not pledge.qty:
				pledge.qty = cint(pledge.amount/pledge.loan_security_price)

			pledge.amount = pledge.qty * pledge.loan_security_price
			pledge.post_haircut_amount = cint(pledge.amount - (pledge.amount * pledge.haircut/100))

			total_security_value += pledge.amount
			maximum_loan_value += pledge.post_haircut_amount

		self.total_security_value = total_security_value
		self.maximum_loan_value = maximum_loan_value

def update_loan(loan, maximum_value_against_pledge):
	maximum_loan_value = frappe.db.get_value('Loan', {'name': loan}, ['maximum_loan_value'])

	frappe.db.sql(""" UPDATE `tabLoan` SET maximum_loan_value=%s, is_secured_loan=1
		WHERE name=%s""", (maximum_loan_value + maximum_value_against_pledge, loan))

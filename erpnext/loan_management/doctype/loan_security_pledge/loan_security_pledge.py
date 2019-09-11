# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class LoanSecurityPledge(Document):
	def validate(self):
		self.set_pledge_amount()

	def set_pledge_amount(self):
		total_security_value = 0
		maximum_loan_value = 0

		for pledge in self.loan_security_pledges:
			pledge.amount = pledge.qty * pledge.loan_security_price

			total_security_value += pledge.amount
			maximum_loan_value += pledge.amount - (pledge.amount * pledge.haircut)/100

		self.total_security_value = total_security_value
		self.maximum_loan_value = maximum_loan_value

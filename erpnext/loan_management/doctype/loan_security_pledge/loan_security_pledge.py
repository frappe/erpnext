# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class LoanSecurityPledge(Document):
	def validate(self):
		self.set_amount()

	def set_amount(self):
		self.amount = self.loan_security_pledge_price * self.qty

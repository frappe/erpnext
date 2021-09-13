# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class LoanType(Document):
	def validate(self):
		self.validate_accounts()

	def validate_accounts(self):
		for fieldname in ['payment_account', 'loan_account', 'interest_income_account', 'penalty_income_account']:
			company = frappe.get_value("Account", self.get(fieldname), 'company')

			if company and company != self.company:
				frappe.throw(_("Account {0} does not belong to company {1}").format(frappe.bold(self.get(fieldname)),
					frappe.bold(self.company)))

		if self.get('loan_account') == self.get('payment_account'):
			frappe.throw(_('Loan Account and Payment Account cannot be same'))

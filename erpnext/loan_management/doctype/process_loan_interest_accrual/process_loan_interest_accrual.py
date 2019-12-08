# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import make_accrual_interest_entry_for_demand_loans

class ProcessLoanInterestAccrual(Document):
	def on_submit(self):
		open_loans = []

		if self.loan:
			open_loans.append(self.loan)

		make_accrual_interest_entry_for_demand_loans(self.posting_date,
			open_loans = open_loans, loan_type = self.loan_type, process_loan_interest=self.name)


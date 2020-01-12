# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import nowdate
from frappe.model.document import Document
from erpnext.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import make_accrual_interest_entry_for_demand_loans

class ProcessLoanInterestAccrual(Document):
	def on_submit(self):
		open_loans = []

		if self.loan:
			loan_doc = frappe.get_doc('Loan', self.loan)
			open_loans.append(loan_doc)

		make_accrual_interest_entry_for_demand_loans(self.posting_date, self.name,
			open_loans = open_loans, loan_type = self.loan_type)

def process_loan_interest_accrual(posting_date=None, loan_type=None, loan=None):
	loan_process = frappe.new_doc('Process Loan Interest Accrual')
	loan_process.posting_date = posting_date or nowdate()
	loan_process.loan_type = loan_type
	loan_process.loan = loan

	loan_process.submit()


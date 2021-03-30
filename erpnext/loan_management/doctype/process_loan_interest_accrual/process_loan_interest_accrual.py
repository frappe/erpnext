# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import nowdate
from frappe.model.document import Document
from erpnext.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (make_accrual_interest_entry_for_demand_loans,
	make_accrual_interest_entry_for_term_loans)

class ProcessLoanInterestAccrual(Document):
	def on_submit(self):
		open_loans = []

		if self.loan:
			loan_doc = frappe.get_doc('Loan', self.loan)
			if loan_doc:
				open_loans.append(loan_doc)

		if (not self.loan or not loan_doc.is_term_loan) and self.process_type != 'Term Loans':
			make_accrual_interest_entry_for_demand_loans(self.posting_date, self.name,
				open_loans = open_loans, loan_type = self.loan_type, accrual_type=self.accrual_type)

		if (not self.loan or loan_doc.is_term_loan) and self.process_type != 'Demand Loans':
			make_accrual_interest_entry_for_term_loans(self.posting_date, self.name, term_loan=self.loan,
				loan_type=self.loan_type, accrual_type=self.accrual_type)


def process_loan_interest_accrual_for_demand_loans(posting_date=None, loan_type=None, loan=None, accrual_type="Regular"):
	loan_process = frappe.new_doc('Process Loan Interest Accrual')
	loan_process.posting_date = posting_date or nowdate()
	loan_process.loan_type = loan_type
	loan_process.process_type = 'Demand Loans'
	loan_process.loan = loan
	loan_process.accrual_type = accrual_type

	loan_process.submit()

	return loan_process.name

def process_loan_interest_accrual_for_term_loans(posting_date=None, loan_type=None, loan=None):

	if not term_loan_accrual_pending(posting_date or nowdate()):
		return

	loan_process = frappe.new_doc('Process Loan Interest Accrual')
	loan_process.posting_date = posting_date or nowdate()
	loan_process.loan_type = loan_type
	loan_process.process_type = 'Term Loans'
	loan_process.loan = loan

	loan_process.submit()

	return loan_process.name

def term_loan_accrual_pending(date):
	pending_accrual = frappe.db.get_value('Repayment Schedule', {
		'payment_date': ('<=', date),
		'is_accrued': 0
	})

	return pending_accrual


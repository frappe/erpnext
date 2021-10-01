# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from erpnext.loan_management.doctype.loan.test_loan import create_loan_accounts, create_loan_type
from erpnext.payroll.doctype.salary_structure.test_salary_structure import (
	make_employee,
	make_salary_structure,
)


class TestLoanApplication(unittest.TestCase):
	def setUp(self):
		create_loan_accounts()
		create_loan_type("Home Loan", 500000, 9.2, 0, 1, 0, 'Cash', 'Payment Account - _TC', 'Loan Account - _TC',
			'Interest Income Account - _TC', 'Penalty Income Account - _TC', 'Repay Over Number of Periods', 18)
		self.applicant = make_employee("kate_loan@loan.com", "_Test Company")
		make_salary_structure("Test Salary Structure Loan", "Monthly", employee=self.applicant, currency='INR')
		self.create_loan_application()

	def create_loan_application(self):
		loan_application = frappe.new_doc("Loan Application")
		loan_application.update({
			"applicant": self.applicant,
			"loan_type": "Home Loan",
			"rate_of_interest": 9.2,
			"loan_amount": 250000,
			"repayment_method": "Repay Over Number of Periods",
			"repayment_periods": 18,
			"company": "_Test Company"
		})
		loan_application.insert()

	def test_loan_totals(self):
		loan_application = frappe.get_doc("Loan Application", {"applicant":self.applicant})

		self.assertEqual(loan_application.total_payable_interest, 18599)
		self.assertEqual(loan_application.total_payable_amount, 268599)
		self.assertEqual(loan_application.repayment_amount, 14923)

		loan_application.repayment_periods = 24
		loan_application.save()
		loan_application.reload()

		self.assertEqual(loan_application.total_payable_interest, 24657)
		self.assertEqual(loan_application.total_payable_amount, 274657)
		self.assertEqual(loan_application.repayment_amount, 11445)

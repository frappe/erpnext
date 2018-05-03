# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.hr.doctype.salary_structure.test_salary_structure import make_employee

class TestLoanApplication(unittest.TestCase):
	def setUp(self):
		self.create_loan_type()
		self.applicant = make_employee("kate_loan@loan.com")
		self.create_loan_application()

	def create_loan_type(self):
		if not frappe.db.get_value("Loan Type", "Home Loan"):
			frappe.get_doc({
				"doctype": "Loan Type",
				"loan_name": "Home Loan",
				"maximum_loan_amount": 500000,
				"rate_of_interest": 9.2
			}).insert()

	def create_loan_application(self):
		if not frappe.db.get_value("Loan Application", {"applicant":self.applicant}, "name"):
			loan_application = frappe.new_doc("Loan Application")
			loan_application.update({
				"applicant": self.applicant,
				"loan_type": "Home Loan",
				"rate_of_interest": 9.2,
				"loan_amount": 250000,
				"repayment_method": "Repay Over Number of Periods",
				"repayment_periods": 24
			})
			loan_application.insert()
	

	def test_loan_totals(self):
		loan_application = frappe.get_doc("Loan Application", {"applicant":self.applicant})
		self.assertEquals(loan_application.repayment_amount, 11445)
		self.assertEquals(loan_application.total_payable_interest, 24657)
		self.assertEquals(loan_application.total_payable_amount, 274657)

		loan_application.repayment_method = "Repay Fixed Amount per Period"
		loan_application.repayment_amount = 15000
		loan_application.save()

		self.assertEqual(loan_application.repayment_periods, 18)
		self.assertEqual(loan_application.total_payable_interest, 18506)
		self.assertEqual(loan_application.total_payable_amount, 268506)
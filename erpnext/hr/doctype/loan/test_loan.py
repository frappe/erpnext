# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import erpnext
import unittest
from frappe.utils import nowdate, add_days
from erpnext.hr.doctype.salary_structure.test_salary_structure import make_employee

class TestLoan(unittest.TestCase):
	def setUp(self):
		create_loan_type("Personal Loan", 500000, 8.4)
		self.applicant = make_employee("robert_loan@loan.com")
		create_loan(self.applicant, "Personal Loan", 280000, "Repay Over Number of Periods", 20)
	
	def test_loan(self):
		loan = frappe.get_doc("Loan", {"applicant":self.applicant})
		self.assertEquals(loan.monthly_repayment_amount, 15052)
		self.assertEquals(loan.total_interest_payable, 21034)
		self.assertEquals(loan.total_payment, 301034)

		schedule = loan.repayment_schedule

		self.assertEqual(len(schedule), 20)

		for idx, principal_amount, interest_amount, balance_loan_amount in [[3, 13369, 1683, 227079], [19, 14941, 105, 0], [17, 14740, 312, 29785]]:
			self.assertEqual(schedule[idx].principal_amount, principal_amount)
			self.assertEqual(schedule[idx].interest_amount, interest_amount)
			self.assertEqual(schedule[idx].balance_loan_amount, balance_loan_amount)

		loan.repayment_method = "Repay Fixed Amount per Period"
		loan.monthly_repayment_amount = 14000
		loan.save()

		self.assertEquals(len(loan.repayment_schedule), 22)
		self.assertEquals(loan.total_interest_payable, 22712)
		self.assertEquals(loan.total_payment, 302712)

def create_loan_type(loan_name, maximum_loan_amount, rate_of_interest):
	if not frappe.db.exists("Loan Type", loan_name):
		frappe.get_doc({
			"doctype": "Loan Type",
			"loan_name": loan_name,
			"maximum_loan_amount": maximum_loan_amount,
			"rate_of_interest": rate_of_interest
		}).insert()

def	create_loan(applicant, loan_type, loan_amount, repayment_method, repayment_periods):
	create_loan_type(loan_type, 500000, 8.4)
	if not frappe.db.get_value("Loan", {"applicant":applicant}):
		loan = frappe.new_doc("Loan")
		loan.update({
				"applicant": applicant,
				"loan_type": loan_type,
				"loan_amount": loan_amount,
				"repayment_method": repayment_method,
				"repayment_periods": repayment_periods,
				"disbursement_date": nowdate(),
				"repayment_start_date": nowdate(),
				"status": "Disbursed",
				"mode_of_payment": frappe.db.get_value('Mode of Payment', {'type': 'Cash'}, 'name'),
				"payment_account": frappe.db.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name"),
				"loan_account": frappe.db.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name"),
				"interest_income_account": frappe.db.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name")
			})
		loan.insert()
		return loan
	else:
		return frappe.get_doc("Loan", {"applicant":applicant})
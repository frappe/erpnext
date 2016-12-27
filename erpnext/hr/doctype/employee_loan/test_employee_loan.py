# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import erpnext
import unittest
from frappe.utils import nowdate
from erpnext.hr.doctype.salary_structure.test_salary_structure import make_employee

class TestEmployeeLoan(unittest.TestCase):
	def setUp(self):
		self.create_loan_type()
		make_employee("robert_loan@loan.com")

	def create_loan_type(self):
		if not frappe.db.get_value("Loan Type", "Personal Loan"):
			frappe.get_doc({
				"doctype": "Loan Type",
				"loan_name": "Personal Loan",
				"maximum_loan_amount": 500000,
				"rate_of_interest": 8.4
			}).insert()
	
	def	create_employee_loan(self):
		if not frappe.db.get_value("Employee Loan", {"employee":"robert_loan@loan.com"}, "name"):
			frappe.get_doc({
				"doctype": "Employee Loan",
				"employee": "robert_loan@loan.com",
				"company": erpnext.get_default_company(),
				"posting_date": nowdate(),
				"loan_type": "Personal Loan",
				"rate_of_interest": 8.4,
				"loan_amount": 280000,
				"repayment_method": "Repay Over Number of Periods",
				"repayment_periods": 20,
				"disbursement_date": nowdate(),
				"mode_of_payment": frappe.db.get_value('Mode of Payment', {'type': 'Cash'}, 'name'),
				"paid_from": frappe.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name")
			}).insert()
	
	def test_employee_loan(self):
		employee_loan = frappe.get_doc("Employee Loan", {"employee":"robert_loan@loan.com"}, "name")
		self.assertEquals(employee_loan.emi_amount, 15052)
		self.assertEquals(employee_loan.total_payable_interest, 21034)
		self.assertEquals(employee_loan.total_payable_amount, 301034)
		self.assertEquals(len(employee_loan.emi_schedule),20)

		employee_loan.repayment_method = "Repay Fixed Amount per Period"
		employee_loan.emi_amount = 14000
		employee_loan.save()

		self.assertEquals(len(employee_loan.emi_schedule),20)
		self.assertEquals(employee_loan.total_payable_interest, 20000)
		self.assertEquals(employee_loan.total_payable_amount, 270000)
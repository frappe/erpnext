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
		create_loan_type("Personal Loan", 500000, 8.4)
		self.employee = make_employee("robert_loan@loan.com")
		create_employee_loan(self.employee, "Personal Loan", 280000, "Repay Over Number of Periods", 20)
	
	def test_employee_loan(self):
		employee_loan = frappe.get_doc("Employee Loan", {"employee":self.employee})
		self.assertEquals(employee_loan.monthly_repayment_amount, 15052)
		self.assertEquals(employee_loan.total_interest_payable, 21034)
		self.assertEquals(employee_loan.total_payment, 301034)

		schedule = employee_loan.repayment_schedule

		self.assertEquals(len(schedule), 20)

		for idx, principal_amount, interest_amount, balance_loan_amount in [[3, 13369, 1683, 227079], [19, 14941, 105, 0], [17, 14740, 312, 29785]]:
			self.assertEquals(schedule[idx].principal_amount, principal_amount)
			self.assertEquals(schedule[idx].interest_amount, interest_amount)
			self.assertEquals(schedule[idx].balance_loan_amount, balance_loan_amount)

		employee_loan.repayment_method = "Repay Fixed Amount per Period"
		employee_loan.monthly_repayment_amount = 14000
		employee_loan.save()

		self.assertEquals(len(employee_loan.repayment_schedule), 22)
		self.assertEquals(employee_loan.total_interest_payable, 22712)
		self.assertEquals(employee_loan.total_payment, 302712)


def create_loan_type(loan_name, maximum_loan_amount, rate_of_interest):
	if not frappe.db.get_value("Loan Type", loan_name):
		frappe.get_doc({
			"doctype": "Loan Type",
			"loan_name": loan_name,
			"maximum_loan_amount": maximum_loan_amount,
			"rate_of_interest": rate_of_interest
		}).insert()

def	create_employee_loan(employee, loan_type, loan_amount, repayment_method, repayment_periods):
	if not frappe.db.get_value("Employee Loan", {"employee":employee}):
		employee_loan = frappe.new_doc("Employee Loan")
		employee_loan.update({
				"employee": employee,
				"loan_type": loan_type,
				"loan_amount": loan_amount,
				"repayment_method": repayment_method,
				"repayment_periods": repayment_periods,
				"disbursement_date": nowdate(),
				"mode_of_payment": frappe.db.get_value('Mode of Payment', {'type': 'Cash'}, 'name'),
				"payment_account": frappe.db.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name"),
				"employee_loan_account": frappe.db.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name"),
				"interest_income_account": frappe.db.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name")
			})
		employee_loan.insert()
		return employee_loan
	else:
		return frappe.get_doc("Employee Loan", {"employee":employee})
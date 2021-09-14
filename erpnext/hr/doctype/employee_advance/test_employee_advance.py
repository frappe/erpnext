# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import nowdate

import erpnext
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.employee_advance.employee_advance import (
	EmployeeAdvanceOverPayment,
	create_return_through_additional_salary,
	make_bank_entry,
)
from erpnext.payroll.doctype.salary_component.test_salary_component import create_salary_component
from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure


class TestEmployeeAdvance(unittest.TestCase):
	def test_paid_amount_and_status(self):
		employee_name = make_employee("_T@employe.advance")
		advance = make_employee_advance(employee_name)

		journal_entry = make_payment_entry(advance)
		journal_entry.submit()

		advance.reload()

		self.assertEqual(advance.paid_amount, 1000)
		self.assertEqual(advance.status, "Paid")

		# try making over payment
		journal_entry1 = make_payment_entry(advance)
		self.assertRaises(EmployeeAdvanceOverPayment, journal_entry1.submit)

	def test_repay_unclaimed_amount_from_salary(self):
		employee_name = make_employee("_T@employe.advance")
		advance = make_employee_advance(employee_name, {"repay_unclaimed_amount_from_salary": 1})

		args = {"type": "Deduction"}
		create_salary_component("Advance Salary - Deduction", **args)
		make_salary_structure("Test Additional Salary for Advance Return", "Monthly", employee=employee_name)

		# additional salary for 700 first
		advance.reload()
		additional_salary = create_return_through_additional_salary(advance)
		additional_salary.salary_component = "Advance Salary - Deduction"
		additional_salary.payroll_date = nowdate()
		additional_salary.amount = 700
		additional_salary.insert()
		additional_salary.submit()

		advance.reload()
		self.assertEqual(advance.return_amount, 700)

		# additional salary for remaining 300
		additional_salary = create_return_through_additional_salary(advance)
		additional_salary.salary_component = "Advance Salary - Deduction"
		additional_salary.payroll_date = nowdate()
		additional_salary.amount = 300
		additional_salary.insert()
		additional_salary.submit()

		advance.reload()
		self.assertEqual(advance.return_amount, 1000)

		# update advance return amount on additional salary cancellation
		additional_salary.cancel()
		advance.reload()
		self.assertEqual(advance.return_amount, 700)

	def tearDown(self):
		frappe.db.rollback()


def make_payment_entry(advance):
	journal_entry = frappe.get_doc(make_bank_entry("Employee Advance", advance.name))
	journal_entry.cheque_no = "123123"
	journal_entry.cheque_date = nowdate()
	journal_entry.save()

	return journal_entry

def make_employee_advance(employee_name, args=None):
	doc = frappe.new_doc("Employee Advance")
	doc.employee = employee_name
	doc.company  = "_Test company"
	doc.purpose = "For site visit"
	doc.currency = erpnext.get_company_currency("_Test company")
	doc.exchange_rate = 1
	doc.advance_amount = 1000
	doc.posting_date = nowdate()
	doc.advance_account = "_Test Employee Advance - _TC"

	if args:
		doc.update(args)

	doc.insert()
	doc.submit()

	return doc

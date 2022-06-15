# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import flt, nowdate

import erpnext
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.employee_advance.employee_advance import (
	EmployeeAdvanceOverPayment,
	create_return_through_additional_salary,
	make_bank_entry,
	make_return_entry,
)
from erpnext.hr.doctype.expense_claim.expense_claim import get_advances
from erpnext.hr.doctype.expense_claim.test_expense_claim import (
	get_payable_account,
	make_expense_claim,
)
from erpnext.payroll.doctype.salary_component.test_salary_component import create_salary_component
from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure


class TestEmployeeAdvance(unittest.TestCase):
	def setUp(self):
		frappe.db.delete("Employee Advance")

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

	def test_paid_amount_on_pe_cancellation(self):
		employee_name = make_employee("_T@employe.advance")
		advance = make_employee_advance(employee_name)

		pe = make_payment_entry(advance)
		pe.submit()

		advance.reload()

		self.assertEqual(advance.paid_amount, 1000)
		self.assertEqual(advance.status, "Paid")

		pe.cancel()
		advance.reload()

		self.assertEqual(advance.paid_amount, 0)
		self.assertEqual(advance.status, "Unpaid")

		advance.cancel()
		advance.reload()
		self.assertEqual(advance.status, "Cancelled")

	def test_claimed_status(self):
		# CLAIMED Status check, full amount claimed
		payable_account = get_payable_account("_Test Company")
		claim = make_expense_claim(
			payable_account, 1000, 1000, "_Test Company", "Travel Expenses - _TC", do_not_submit=True
		)

		advance = make_employee_advance(claim.employee)
		pe = make_payment_entry(advance)
		pe.submit()

		claim = get_advances_for_claim(claim, advance.name)
		claim.save()
		claim.submit()

		advance.reload()
		self.assertEqual(advance.claimed_amount, 1000)
		self.assertEqual(advance.status, "Claimed")

		# advance should not be shown in claims
		advances = get_advances(claim.employee)
		advances = [entry.name for entry in advances]
		self.assertTrue(advance.name not in advances)

		# cancel claim; status should be Paid
		claim.cancel()
		advance.reload()
		self.assertEqual(advance.claimed_amount, 0)
		self.assertEqual(advance.status, "Paid")

	def test_partly_claimed_and_returned_status(self):
		payable_account = get_payable_account("_Test Company")
		claim = make_expense_claim(
			payable_account, 1000, 1000, "_Test Company", "Travel Expenses - _TC", do_not_submit=True
		)

		advance = make_employee_advance(claim.employee)
		pe = make_payment_entry(advance)
		pe.submit()

		# PARTLY CLAIMED AND RETURNED status check
		# 500 Claimed, 500 Returned
		claim = make_expense_claim(
			payable_account, 500, 500, "_Test Company", "Travel Expenses - _TC", do_not_submit=True
		)

		advance = make_employee_advance(claim.employee)
		pe = make_payment_entry(advance)
		pe.submit()

		claim = get_advances_for_claim(claim, advance.name, amount=500)
		claim.save()
		claim.submit()

		advance.reload()
		self.assertEqual(advance.claimed_amount, 500)
		self.assertEqual(advance.status, "Paid")

		entry = make_return_entry(
			employee=advance.employee,
			company=advance.company,
			employee_advance_name=advance.name,
			return_amount=flt(advance.paid_amount - advance.claimed_amount),
			advance_account=advance.advance_account,
			mode_of_payment=advance.mode_of_payment,
			currency=advance.currency,
			exchange_rate=advance.exchange_rate,
		)

		entry = frappe.get_doc(entry)
		entry.insert()
		entry.submit()

		advance.reload()
		self.assertEqual(advance.return_amount, 500)
		self.assertEqual(advance.status, "Partly Claimed and Returned")

		# advance should not be shown in claims
		advances = get_advances(claim.employee)
		advances = [entry.name for entry in advances]
		self.assertTrue(advance.name not in advances)

		# Cancel return entry; status should change to PAID
		entry.cancel()
		advance.reload()
		self.assertEqual(advance.return_amount, 0)
		self.assertEqual(advance.status, "Paid")

		# advance should be shown in claims
		advances = get_advances(claim.employee)
		advances = [entry.name for entry in advances]
		self.assertTrue(advance.name in advances)

	def test_repay_unclaimed_amount_from_salary(self):
		employee_name = make_employee("_T@employe.advance")
		advance = make_employee_advance(employee_name, {"repay_unclaimed_amount_from_salary": 1})
		pe = make_payment_entry(advance)
		pe.submit()

		args = {"type": "Deduction"}
		create_salary_component("Advance Salary - Deduction", **args)
		make_salary_structure(
			"Test Additional Salary for Advance Return", "Monthly", employee=employee_name
		)

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
		self.assertEqual(advance.status, "Returned")

		# update advance return amount on additional salary cancellation
		additional_salary.cancel()
		advance.reload()
		self.assertEqual(advance.return_amount, 700)
		self.assertEqual(advance.status, "Paid")

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
	doc.company = "_Test Company"
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


def get_advances_for_claim(claim, advance_name, amount=None):
	advances = get_advances(claim.employee, advance_name)

	for entry in advances:
		if amount:
			allocated_amount = amount
		else:
			allocated_amount = flt(entry.paid_amount) - flt(entry.claimed_amount)

		claim.append(
			"advances",
			{
				"employee_advance": entry.name,
				"posting_date": entry.posting_date,
				"advance_account": entry.advance_account,
				"advance_paid": entry.paid_amount,
				"unclaimed_amount": allocated_amount,
				"allocated_amount": allocated_amount,
			},
		)

	return claim

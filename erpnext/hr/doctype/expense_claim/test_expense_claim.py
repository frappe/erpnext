# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate, random_string

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.expense_claim.expense_claim import make_bank_entry

test_dependencies = ["Employee"]
company_name = "_Test Company 3"


class TestExpenseClaim(FrappeTestCase):
	def setUp(self):
		if not frappe.db.get_value("Cost Center", {"company": company_name}):
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "_Test Cost Center 3",
					"parent_cost_center": "_Test Company 3 - _TC3",
					"is_group": 0,
					"company": company_name,
				}
			).insert()

	def test_total_expense_claim_for_project(self):
		frappe.db.sql("""delete from `tabTask`""")
		frappe.db.sql("""delete from `tabProject`""")
		frappe.db.sql("update `tabExpense Claim` set project = '', task = ''")

		project = frappe.get_doc({"project_name": "_Test Project 1", "doctype": "Project"})
		project.save()

		task = frappe.get_doc(
			dict(doctype="Task", subject="_Test Project Task 1", status="Open", project=project.name)
		).insert()

		task_name = task.name
		payable_account = get_payable_account(company_name)

		make_expense_claim(
			payable_account, 300, 200, company_name, "Travel Expenses - _TC3", project.name, task_name
		)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 200)
		self.assertEqual(frappe.db.get_value("Project", project.name, "total_expense_claim"), 200)

		expense_claim2 = make_expense_claim(
			payable_account, 600, 500, company_name, "Travel Expenses - _TC3", project.name, task_name
		)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 700)
		self.assertEqual(frappe.db.get_value("Project", project.name, "total_expense_claim"), 700)

		expense_claim2.cancel()

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 200)
		self.assertEqual(frappe.db.get_value("Project", project.name, "total_expense_claim"), 200)

	def test_expense_claim_status(self):
		payable_account = get_payable_account(company_name)
		expense_claim = make_expense_claim(
			payable_account, 300, 200, company_name, "Travel Expenses - _TC3"
		)

		je = make_journal_entry(expense_claim)

		expense_claim = frappe.get_doc("Expense Claim", expense_claim.name)
		self.assertEqual(expense_claim.status, "Paid")

		je.cancel()
		expense_claim = frappe.get_doc("Expense Claim", expense_claim.name)
		self.assertEqual(expense_claim.status, "Unpaid")

		# expense claim without any sanctioned amount should not have status as Paid
		claim = make_expense_claim(payable_account, 1000, 0, "_Test Company", "Travel Expenses - _TC")
		self.assertEqual(claim.total_sanctioned_amount, 0)
		self.assertEqual(claim.status, "Submitted")

		# no gl entries created
		gl_entry = frappe.get_all(
			"GL Entry", {"voucher_type": "Expense Claim", "voucher_no": claim.name}
		)
		self.assertEqual(len(gl_entry), 0)

	def test_expense_claim_against_fully_paid_advances(self):
		from erpnext.hr.doctype.employee_advance.test_employee_advance import (
			get_advances_for_claim,
			make_employee_advance,
			make_payment_entry,
		)

		frappe.db.delete("Employee Advance")

		payable_account = get_payable_account("_Test Company")
		claim = make_expense_claim(
			payable_account, 1000, 1000, "_Test Company", "Travel Expenses - _TC", do_not_submit=True
		)

		advance = make_employee_advance(claim.employee)
		pe = make_payment_entry(advance)
		pe.submit()

		# claim for already paid out advances
		claim = get_advances_for_claim(claim, advance.name)
		claim.save()
		claim.submit()

		self.assertEqual(claim.grand_total, 0)
		self.assertEqual(claim.status, "Paid")

	def test_advance_amount_allocation_against_claim_with_taxes(self):
		from erpnext.hr.doctype.employee_advance.test_employee_advance import (
			get_advances_for_claim,
			make_employee_advance,
			make_payment_entry,
		)

		frappe.db.delete("Employee Advance")

		payable_account = get_payable_account("_Test Company")
		taxes = generate_taxes("_Test Company")
		claim = make_expense_claim(
			payable_account,
			700,
			700,
			"_Test Company",
			"Travel Expenses - _TC",
			do_not_submit=True,
			taxes=taxes,
		)
		claim.save()

		advance = make_employee_advance(claim.employee)
		pe = make_payment_entry(advance)
		pe.submit()

		# claim for already paid out advances
		claim = get_advances_for_claim(claim, advance.name, 763)
		claim.save()
		claim.submit()

		self.assertEqual(claim.grand_total, 0)
		self.assertEqual(claim.status, "Paid")

	def test_expense_claim_partially_paid_via_advance(self):
		from erpnext.hr.doctype.employee_advance.test_employee_advance import (
			get_advances_for_claim,
			make_employee_advance,
		)
		from erpnext.hr.doctype.employee_advance.test_employee_advance import (
			make_payment_entry as make_advance_payment,
		)

		frappe.db.delete("Employee Advance")

		payable_account = get_payable_account("_Test Company")
		claim = make_expense_claim(
			payable_account, 1000, 1000, "_Test Company", "Travel Expenses - _TC", do_not_submit=True
		)

		# link advance for partial amount
		advance = make_employee_advance(claim.employee, {"advance_amount": 500})
		pe = make_advance_payment(advance)
		pe.submit()

		claim = get_advances_for_claim(claim, advance.name)
		claim.save()
		claim.submit()

		self.assertEqual(claim.grand_total, 500)
		self.assertEqual(claim.status, "Unpaid")

		# reimburse remaning amount
		make_payment_entry(claim, payable_account, 500)
		claim.reload()

		self.assertEqual(claim.total_amount_reimbursed, 500)
		self.assertEqual(claim.status, "Paid")

	def test_expense_claim_gl_entry(self):
		payable_account = get_payable_account(company_name)
		taxes = generate_taxes()
		expense_claim = make_expense_claim(
			payable_account,
			300,
			200,
			company_name,
			"Travel Expenses - _TC3",
			do_not_submit=True,
			taxes=taxes,
		)
		expense_claim.submit()

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Expense Claim' and voucher_no=%s
			order by account asc""",
			expense_claim.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		expected_values = dict(
			(d[0], d)
			for d in [
				["Output Tax CGST - _TC3", 18.0, 0.0],
				[payable_account, 0.0, 218.0],
				["Travel Expenses - _TC3", 200.0, 0.0],
			]
		)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)

	def test_rejected_expense_claim(self):
		payable_account = get_payable_account(company_name)
		expense_claim = frappe.get_doc(
			{
				"doctype": "Expense Claim",
				"employee": "_T-Employee-00001",
				"payable_account": payable_account,
				"approval_status": "Rejected",
				"expenses": [
					{
						"expense_type": "Travel",
						"default_account": "Travel Expenses - _TC3",
						"amount": 300,
						"sanctioned_amount": 200,
					}
				],
			}
		)
		expense_claim.submit()

		self.assertEqual(expense_claim.status, "Rejected")
		self.assertEqual(expense_claim.total_sanctioned_amount, 0.0)

		gl_entry = frappe.get_all(
			"GL Entry", {"voucher_type": "Expense Claim", "voucher_no": expense_claim.name}
		)
		self.assertEqual(len(gl_entry), 0)

	def test_expense_approver_perms(self):
		user = "test_approver_perm_emp@example.com"
		make_employee(user, "_Test Company")

		# check doc shared
		payable_account = get_payable_account("_Test Company")
		expense_claim = make_expense_claim(
			payable_account, 300, 200, "_Test Company", "Travel Expenses - _TC", do_not_submit=True
		)
		expense_claim.expense_approver = user
		expense_claim.save()
		self.assertTrue(expense_claim.name in frappe.share.get_shared("Expense Claim", user))

		# check shared doc revoked
		expense_claim.reload()
		expense_claim.expense_approver = "test@example.com"
		expense_claim.save()
		self.assertTrue(expense_claim.name not in frappe.share.get_shared("Expense Claim", user))

		expense_claim.reload()
		expense_claim.expense_approver = user
		expense_claim.save()

		frappe.set_user(user)
		expense_claim.reload()
		expense_claim.status = "Approved"
		expense_claim.submit()
		frappe.set_user("Administrator")

	def test_multiple_payment_entries_against_expense(self):
		# Creating expense claim
		payable_account = get_payable_account("_Test Company")
		expense_claim = make_expense_claim(
			payable_account, 5500, 5500, "_Test Company", "Travel Expenses - _TC"
		)
		expense_claim.save()
		expense_claim.submit()

		# Payment entry 1: paying 500
		make_payment_entry(expense_claim, payable_account, 500)
		outstanding_amount, total_amount_reimbursed = get_outstanding_and_total_reimbursed_amounts(
			expense_claim
		)
		self.assertEqual(outstanding_amount, 5000)
		self.assertEqual(total_amount_reimbursed, 500)

		# Payment entry 1: paying 2000
		make_payment_entry(expense_claim, payable_account, 2000)
		outstanding_amount, total_amount_reimbursed = get_outstanding_and_total_reimbursed_amounts(
			expense_claim
		)
		self.assertEqual(outstanding_amount, 3000)
		self.assertEqual(total_amount_reimbursed, 2500)

		# Payment entry 1: paying 3000
		make_payment_entry(expense_claim, payable_account, 3000)
		outstanding_amount, total_amount_reimbursed = get_outstanding_and_total_reimbursed_amounts(
			expense_claim
		)
		self.assertEqual(outstanding_amount, 0)
		self.assertEqual(total_amount_reimbursed, 5500)

	def test_journal_entry_against_expense_claim(self):
		payable_account = get_payable_account(company_name)
		taxes = generate_taxes()
		expense_claim = make_expense_claim(
			payable_account,
			300,
			200,
			company_name,
			"Travel Expenses - _TC3",
			do_not_submit=True,
			taxes=taxes,
		)
		expense_claim.submit()

		je = make_journal_entry(expense_claim)

		self.assertEqual(je.accounts[0].debit_in_account_currency, expense_claim.grand_total)


def get_payable_account(company):
	return frappe.get_cached_value("Company", company, "default_payable_account")


def generate_taxes(company=None):
	company = company or company_name
	parent_account = frappe.db.get_value(
		"Account", filters={"account_name": "Duties and Taxes", "company": company}
	)
	account = create_account(
		company=company,
		account_name="Output Tax CGST",
		account_type="Tax",
		parent_account=parent_account,
	)
	return {
		"taxes": [
			{"account_head": account, "rate": 9, "description": "CGST", "tax_amount": 10, "total": 210}
		]
	}


def make_expense_claim(
	payable_account,
	amount,
	sanctioned_amount,
	company,
	account,
	project=None,
	task_name=None,
	do_not_submit=False,
	taxes=None,
):
	employee = frappe.db.get_value("Employee", {"status": "Active"})
	if not employee:
		employee = make_employee("test_employee@expense_claim.com", company=company)

	currency, cost_center = frappe.db.get_value(
		"Company", company, ["default_currency", "cost_center"]
	)
	expense_claim = {
		"doctype": "Expense Claim",
		"employee": employee,
		"payable_account": payable_account,
		"approval_status": "Approved",
		"company": company,
		"currency": currency,
		"expenses": [
			{
				"expense_type": "Travel",
				"default_account": account,
				"currency": currency,
				"amount": amount,
				"sanctioned_amount": sanctioned_amount,
				"cost_center": cost_center,
			}
		],
	}
	if taxes:
		expense_claim.update(taxes)

	expense_claim = frappe.get_doc(expense_claim)

	if project:
		expense_claim.project = project
	if task_name:
		expense_claim.task = task_name

	if do_not_submit:
		return expense_claim
	expense_claim.submit()
	return expense_claim


def get_outstanding_and_total_reimbursed_amounts(expense_claim):
	outstanding_amount = flt(
		frappe.db.get_value("Expense Claim", expense_claim.name, "total_sanctioned_amount")
	) - flt(frappe.db.get_value("Expense Claim", expense_claim.name, "total_amount_reimbursed"))
	total_amount_reimbursed = flt(
		frappe.db.get_value("Expense Claim", expense_claim.name, "total_amount_reimbursed")
	)

	return outstanding_amount, total_amount_reimbursed


def make_payment_entry(expense_claim, payable_account, amt):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry(
		"Expense Claim", expense_claim.name, bank_account="_Test Bank USD - _TC", bank_amount=amt
	)
	pe.reference_no = "1"
	pe.reference_date = nowdate()
	pe.source_exchange_rate = 1
	pe.paid_to = payable_account
	pe.references[0].allocated_amount = amt
	pe.insert()
	pe.submit()


def make_journal_entry(expense_claim):
	je_dict = make_bank_entry("Expense Claim", expense_claim.name)
	je = frappe.get_doc(je_dict)
	je.posting_date = nowdate()
	je.cheque_no = random_string(5)
	je.cheque_date = nowdate()
	je.submit()

	return je

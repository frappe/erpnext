# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import random_string, nowdate
from erpnext.hr.doctype.expense_claim.expense_claim import make_bank_entry
from erpnext.accounts.doctype.account.test_account import create_account

test_records = frappe.get_test_records('Expense Claim')
test_dependencies = ['Employee']

class TestExpenseClaim(unittest.TestCase):
	def test_total_expense_claim_for_project(self):
		frappe.db.sql("""delete from `tabTask` where project = "_Test Project 1" """)
		frappe.db.sql("""delete from `tabProject` where name = "_Test Project 1" """)


		frappe.get_doc({
			"project_name": "_Test Project 1",
			"doctype": "Project",
			"tasks" :
				[{ "title": "_Test Project Task 1", "status": "Open" }]
		}).save()

		task_name = frappe.db.get_value("Task", {"project": "_Test Project 1"})
		payable_account = get_payable_account("Wind Power LLC")

		make_expense_claim(payable_account, 300, 200, "Wind Power LLC", "Travel Expenses - WP", "_Test Project 1", task_name)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"), 200)

		expense_claim2 = make_expense_claim(payable_account, 600, 500, "Wind Power LLC", "Travel Expenses - WP","_Test Project 1", task_name)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 700)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"), 700)

		expense_claim2.cancel()
		frappe.delete_doc("Expense Claim", expense_claim2.name)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"), 200)

	def test_expense_claim_status(self):
		payable_account = get_payable_account("Wind Power LLC")
		expense_claim = make_expense_claim(payable_account, 300, 200, "Wind Power LLC", "Travel Expenses - WP")

		je_dict = make_bank_entry("Expense Claim", expense_claim.name)
		je = frappe.get_doc(je_dict)
		je.posting_date = nowdate()
		je.cheque_no = random_string(5)
		je.cheque_date = nowdate()
		je.submit()

		expense_claim = frappe.get_doc("Expense Claim", expense_claim.name)
		self.assertEqual(expense_claim.status, "Paid")

		je.cancel()
		expense_claim = frappe.get_doc("Expense Claim", expense_claim.name)
		self.assertEqual(expense_claim.status, "Unpaid")

	def test_expense_claim_gl_entry(self):
		payable_account = get_payable_account("Wind Power LLC")
		taxes = generate_taxes()
		expense_claim = make_expense_claim(payable_account, 300, 200, "Wind Power LLC", "Travel Expenses - WP", do_not_submit=True, taxes=taxes)
		expense_claim.submit()

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Expense Claim' and voucher_no=%s
			order by account asc""", expense_claim.name, as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = dict((d[0], d) for d in [
			['CGST - WP',10.0, 0.0],
			[payable_account, 0.0, 210.0],
			["Travel Expenses - WP", 200.0, 0.0]
		])

		for gle in gl_entries:
			self.assertEquals(expected_values[gle.account][0], gle.account)
			self.assertEquals(expected_values[gle.account][1], gle.debit)
			self.assertEquals(expected_values[gle.account][2], gle.credit)

	def test_rejected_expense_claim(self):
		payable_account = get_payable_account("Wind Power LLC")
		expense_claim = frappe.get_doc({
			 "doctype": "Expense Claim",
			 "employee": "_T-Employee-00001",
			 "payable_account": payable_account,
			 "approval_status": "Rejected",
			 "expenses":
			 	[{ "expense_type": "Travel", "default_account": "Travel Expenses - WP", "amount": 300, "sanctioned_amount": 200 }]
		})
		expense_claim.submit()

		self.assertEquals(expense_claim.status, 'Rejected')
		self.assertEquals(expense_claim.total_sanctioned_amount, 0.0)

		gl_entry = frappe.get_all('GL Entry', {'voucher_type': 'Expense Claim', 'voucher_no': expense_claim.name})
		self.assertEquals(len(gl_entry), 0)

def get_payable_account(company):
	return frappe.get_cached_value('Company', company, 'default_payable_account')

def generate_taxes():
	parent_account = frappe.db.get_value('Account',
		{'company': "Wind Power LLC", 'is_group':1, 'account_type': 'Tax'},
		'name')
	account = create_account(company="Wind Power LLC", account_name="CGST", account_type="Tax", parent_account=parent_account)
	return {'taxes':[{
		"account_head": account,
		"rate": 0,
		"description": "CGST",
		"tax_amount": 10,
		"total": 210
	}]}

def make_expense_claim(payable_account, amount, sanctioned_amount, company, account, project=None, task_name=None, do_not_submit=False, taxes=None):
	expense_claim = {
		 "doctype": "Expense Claim",
		 "employee": "_T-Employee-00001",
		 "payable_account": payable_account,
		 "approval_status": "Approved",
		 "company": company,
		 "expenses":
			[{"expense_type": "Travel",
			"default_account": account,
			"amount": amount,
			"sanctioned_amount": sanctioned_amount}]}
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

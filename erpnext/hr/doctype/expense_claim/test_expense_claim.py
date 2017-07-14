# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import random_string, nowdate
from frappe import _
from erpnext.hr.doctype.expense_claim.expense_claim import make_bank_entry

test_records = frappe.get_test_records('Expense Claim')

class TestExpenseClaim(unittest.TestCase):
	def test_total_expense_claim_for_project(self):
		frappe.db.sql("""delete from `tabTask` where project = "_Test Project 1" """)
		frappe.db.sql("""delete from `tabProject` where name = "_Test Project 1" """)

		set_tax_accounts("Wind Power LLC")

		frappe.get_doc({
			"project_name": "_Test Project 1",
			"doctype": "Project",
			"tasks" :
				[{ "title": "_Test Project Task 1", "status": "Open" }]
		}).save()

		task_name = frappe.db.get_value("Task", {"project": "_Test Project 1"})
		payable_account = get_payable_account("Wind Power LLC")

		expense_claim = frappe.get_doc({
			 "doctype": "Expense Claim",
			 "employee": "_T-Employee-0001",
			 "payable_account": payable_account,
			 "approval_status": "Approved",
			 "project": "_Test Project 1",
			 "task": task_name,
			 "expenses":
			 	[{ "expense_type": "Travel", "default_account": "Travel Expenses - WP", "claim_amount": 400, "sanctioned_amount": 300, "tax_amount": 10, "sanctioned_tax": 7.50 }]
		})
		expense_claim.submit()

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 300)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"), 300)

		expense_claim2 = frappe.get_doc({
			 "doctype": "Expense Claim",
			 "employee": "_T-Employee-0001",
			 "approval_status": "Approved",
			 "project": "_Test Project 1",
			 "task": task_name,
			 "expenses":
			 	[{ "expense_type": "Travel", "default_account": "Travel Expenses - WP", "claim_amount": 600, "sanctioned_amount": 500, "tax_amount": 60, "sanctioned_tax": 50 }]
		})
		expense_claim2.submit()

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 800)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"), 800)

		expense_claim2.cancel()
		frappe.delete_doc("Expenses Claim", expense_claim2.name)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 300)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"), 300)

		expense_claim.cancel()

	def test_expense_claim_status(self):
		set_tax_accounts("Wind Power LLC")
		payable_account = get_payable_account("Wind Power LLC")
		expense_claim = frappe.get_doc({
			 "doctype": "Expense Claim",
			 "employee": "_T-Employee-0001",
			 "payable_account": payable_account,
			 "approval_status": "Approved",
			 "expenses":
			 	[{ "expense_type": "Travel", "default_account": "Travel Expenses - WP", "claim_amount": 300, "sanctioned_amount": 200, "tax_amount": 30, "sanctioned_tax": 20 }]
		})
		expense_claim.submit()

		je_dict = make_bank_entry(expense_claim.name)
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
		set_tax_accounts("Wind Power LLC")
		payable_account = get_payable_account("Wind Power LLC")
		expense_claim = frappe.get_doc({
			 "doctype": "Expense Claim",
			 "employee": "_T-Employee-0001",
			 "payable_account": payable_account,
			 "approval_status": "Approved",
			 "expenses":
			 	[{ "expense_type": "Travel", "default_account": "Travel Expenses - WP", "claim_amount": 300, "sanctioned_amount": 200, "tax_amount": 15, "sanctioned_tax": 10 }]
		})
		expense_claim.submit()

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Expense Claim' and voucher_no=%s
			order by account asc""", expense_claim.name, as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = dict((d[0], d) for d in [
			[payable_account, 0.0, 200.0],
			["Travel Expenses - WP", 190.0, 0.0],
			["Miscellaneous Expenses - WP", 10.0, 0.0]
		])
		expense_claim.cancel()

		for gle in gl_entries:
			self.assertEquals(expected_values[gle.account][0], gle.account)
			self.assertEquals(expected_values[gle.account][1], gle.debit)
			self.assertEquals(expected_values[gle.account][2], gle.credit)

def get_payable_account(company):
	return frappe.db.get_value('Company', company, 'default_payable_account')

def set_tax_accounts(company):
	company_abbr = frappe.db.get_value("Company", company, "abbr")
	tax_expense_types = [{'name': _('Travel'), "tax_account": "Miscellaneous Expenses - "+ company_abbr}]

	for expense_type in tax_expense_types:
		doc = frappe.get_doc("Expense Claim Type", expense_type["name"])
		if len(doc.tax_accounts) == 0:
			doc.append("tax_accounts", {
				"company" : company,
				"default_account" : expense_type["tax_account"]
			})
			doc.save(ignore_permissions=True)

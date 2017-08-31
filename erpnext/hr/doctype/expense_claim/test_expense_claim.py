# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import random_string, nowdate
from erpnext.hr.doctype.expense_claim.expense_claim import make_bank_entry
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

test_records = frappe.get_test_records('Expense Claim')

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

		existing_claimed_amount = frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim")
		task_name = frappe.db.get_value("Task", {"project": "_Test Project 1"})
		payable_account = get_payable_account("Wind Power LLC")

		make_expense_claim(300, 200,"Travel Expenses - WP", "Wind Power LLC",
			payable_account, "_Test Project 1", task_name)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"),
			existing_claimed_amount + 200)

		expense_claim2 = make_expense_claim(600, 500, "Travel Expenses - WP", "Wind Power LLC",
			payable_account, "_Test Project 1", task_name)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 700)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"),
			existing_claimed_amount + 700)

		expense_claim2.cancel()
		frappe.delete_doc("Expense Claim", expense_claim2.name)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"),
			existing_claimed_amount+200)

	def test_expense_claim_status(self):
		payable_account = get_payable_account("Wind Power LLC")
		expense_claim = make_expense_claim(300, 200, "Travel Expenses - WP",
			"Wind Power LLC", payable_account)

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
		expense_claim = make_expense_claim(300, 200, "Travel Expenses - WP",
			"Wind Power LLC", payable_account)
		expense_claim.submit()

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Expense Claim' and voucher_no=%s
			order by account asc""", expense_claim.name, as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = dict((d[0], d) for d in [
			[payable_account, 0.0, 200.0],
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
			 "employee": "_T-Employee-0001",
			 "payable_account": payable_account,
			 "approval_status": "Rejected",
			 "expenses":
			 	[{ "expense_type": "Travel", "default_account": "Travel Expenses - WP", "claim_amount": 300, "sanctioned_amount": 200 }]
		})
		expense_claim.submit()

		self.assertEquals(expense_claim.status, 'Rejected')
		self.assertEquals(expense_claim.total_sanctioned_amount, 0.0)

		gl_entry = frappe.get_all('GL Entry', {'voucher_type': 'Expense Claim', 'voucher_no': expense_claim.name})
		self.assertEquals(len(gl_entry), 0)

	def test_advance_payment(self):
		expense_claim = make_expense_claim(150, 150, "Travel Expenses - _TC",
			advance_required=1, submit=False)

		payment_entry = get_payment_entry("Expense Claim", expense_claim.name, bank_amount=50)
		payment_entry.received_amount = payment_entry.paid_amount = 50
		payment_entry.get("references")[0].allocated_amount = 50
		payment_entry.reference_no = "1"
		payment_entry.reference_date = "2016-01-01"
		payment_entry.save()
		payment_entry.submit()

		expense_claim.load_from_db()
		self.assertEqual(expense_claim.total_advance_paid, 50)

		expense_claim.submit()
		payment_entry = get_payment_entry("Expense Claim", expense_claim.name)
		payment_entry.reference_no = "1"
		payment_entry.reference_date = "2016-01-01"
		payment_entry.save()
		payment_entry.submit()

		expense_claim.load_from_db()
		self.assertEqual(expense_claim.total_advance_paid, 50)
		self.assertEqual(expense_claim.total_amount_reimbursed, 100)

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Expense Claim' and voucher_no=%s
			order by account asc""", expense_claim.name, as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = dict((d[0], d) for d in [
			[get_advance_account("_Test Company"), 0.0, 50.0],
			[get_payable_account("_Test Company"), 0.0, 100.0],
			["Travel Expenses - _TC", 150.0, 0.0]
		])

		for gle in gl_entries:
			self.assertEquals(expected_values[gle.account][0], gle.account)
			self.assertEquals(expected_values[gle.account][1], gle.debit)
			self.assertEquals(expected_values[gle.account][2], gle.credit)

def get_payable_account(company):
	return frappe.db.get_value('Company', company, 'default_payable_account')

def get_advance_account(company):
	return frappe.db.get_value('Company', company, 'default_advance_account') \
		or frappe.db.get_value('Company', company, 'default_receivable_account')

def make_expense_claim(claim_amount, sanctioned_amount, expense_account, company="_Test Company",
		payable_account=None, project=None, task_name=None, 
		advance_required=0, advance_account=None, submit=True):
	expense_claim = frappe.get_doc({
		 "doctype": "Expense Claim",
		 "employee": "_T-Employee-0001",
		 "payable_account": payable_account or get_payable_account(company),
		 "advance_account": advance_account or get_advance_account(company),
		 "advance_required": advance_required,
		 "approval_status": "Approved",
		 "company": company,
		 "expenses": [{
			 "expense_type": "Travel",
			 "default_account": expense_account,
			 "claim_amount": claim_amount,
			 "sanctioned_amount": sanctioned_amount
		 }]
	})
	if project:
		expense_claim.project = project
	if task_name:
		expense_claim.task = task_name

	expense_claim.save()
	if submit:
		expense_claim.submit()
	return expense_claim



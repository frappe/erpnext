# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_records = frappe.get_test_records('Expense Claim')

class TestExpenseClaim(unittest.TestCase):
	def test_total_expense_claim_for_project(self):
		frappe.db.sql("""delete from `tabTask` where project = "_Test Project 1" """)
		frappe.db.sql("""delete from `tabProject` where name = "_Test Project 1" """)
		frappe.db.sql("""delete from `tabExpense Claim`""")
		frappe.db.sql("""delete from `tabExpense Claim Detail`""")

		frappe.get_doc({
			"project_name": "_Test Project 1",
			"doctype": "Project",
			"tasks" :
				[{ "title": "_Test Project Task 1", "status": "Open" }]
		}).save()

		task_name = frappe.db.get_value("Task", {"project": "_Test Project 1"})

		expense_claim = frappe.get_doc({
			 "doctype": "Expense Claim",
			 "employee": "_T-Employee-0001",
			 "approval_status": "Approved",
			 "project": "_Test Project 1",
			 "task": task_name,
			 "expenses":
			 	[{ "expense_type": "Food", "default_account": "Entertainment Expenses - _TC", "claim_amount": 300, "sanctioned_amount": 200 }]
		})
		expense_claim.submit()

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"), 200)

		expense_claim2 = frappe.get_doc({
			 "doctype": "Expense Claim",
			 "employee": "_T-Employee-0001",
			 "approval_status": "Approved",
			 "project": "_Test Project 1",
			 "task": task_name,
			 "expenses":
			 	[{ "expense_type": "Food", "default_account": "Entertainment Expenses - _TC", "claim_amount": 600, "sanctioned_amount": 500 }]
		})
		expense_claim2.submit()

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 700)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"), 700)

		expense_claim2.cancel()

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_expense_claim"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_expense_claim"), 200)

# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.doctype.budget.budget import get_actual_expense, BudgetError
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

class TestBudget(unittest.TestCase):		
	def test_monthly_budget_crossed_ignore(self):
		set_total_expense_zero("2013-02-28", "Cost Center")

		budget = make_budget("Cost Center")
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv.name}))
			
		budget.cancel()

	def test_monthly_budget_crossed_stop1(self):
		set_total_expense_zero("2013-02-28", "Cost Center")

		budget = make_budget("Cost Center")
		
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_crossed_stop2(self):
		set_total_expense_zero("2013-02-28", "Project")

		budget = make_budget("Project")
		
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC", project="_Test Project")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.load_from_db()
		budget.cancel()

	def test_yearly_budget_crossed_stop1(self):
		set_total_expense_zero("2013-02-28", "Cost Center")

		budget = make_budget("Cost Center")
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 150000, "_Test Cost Center - _TC")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.cancel()

	def test_yearly_budget_crossed_stop2(self):
		set_total_expense_zero("2013-02-28", "Project")

		budget = make_budget("Project")
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 150000, "_Test Cost Center - _TC", project="_Test Project")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.cancel()

	def test_monthly_budget_on_cancellation1(self):
		set_total_expense_zero("2013-02-28", "Cost Center")

		budget = make_budget("Cost Center")
				
		jv1 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv1.name}))

		jv2 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv2.name}))

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
		
		self.assertRaises(BudgetError, jv1.cancel)
		
		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_on_cancellation2(self):
		set_total_expense_zero("2013-02-28", "Project")

		budget = make_budget("Project")
				
		jv1 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", submit=True, project="_Test Project")

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv1.name}))

		jv2 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", submit=True, project="_Test Project")

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv2.name}))

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
		
		self.assertRaises(BudgetError, jv1.cancel)
		
		budget.load_from_db()
		budget.cancel()

		
	def test_monthly_budget_against_group_cost_center(self):
		set_total_expense_zero("2013-02-28", "Cost Center")
		set_total_expense_zero("2013-02-28", "Cost Center", "_Test Cost Center 2 - _TC")
		
		budget = make_budget("Cost Center", "_Test Company - _TC")
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center 2 - _TC")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.load_from_db()
		budget.cancel()

def set_total_expense_zero(posting_date, budget_against_field=None, budget_against_CC=None):
	if budget_against_field == "Project":
		budget_against = "_Test Project"
	else:
		budget_against = budget_against_CC or "_Test Cost Center - _TC"
	existing_expense = get_actual_expense(frappe._dict({
		"account": "_Test Account Cost for Goods Sold - _TC",
		"cost_center": "_Test Cost Center - _TC",
		"monthly_end_date": posting_date,
		"company": "_Test Company",
		"fiscal_year": "_Test Fiscal Year 2013",
		"budget_against_field": budget_against_field,
		"budget_against": budget_against
	}))
	
	if existing_expense:
		if budget_against_field == "Cost Center":
			make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", -existing_expense, "_Test Cost Center - _TC", submit=True)
		elif budget_against_field == "Project":
			make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", -existing_expense, "_Test Cost Center - _TC", submit=True, project="_Test Project")
		
def make_budget(budget_against=None, cost_center=None):
	if budget_against == "Project":
		budget_list = frappe.get_all("Budget", fields=["name"], filters = {"name": ("like", "_Test Project/_Test Fiscal Year 2013%")})
	else:
		budget_list = frappe.get_all("Budget", fields=["name"], filters = {"name": ("like", "_Test Cost Center - _TC/_Test Fiscal Year 2013%")})
	for d in budget_list:
		frappe.db.sql("delete from `tabBudget` where name = %(name)s", d)
		frappe.db.sql("delete from `tabBudget Account` where parent = %(name)s", d)

	budget = frappe.new_doc("Budget")
	
	if budget_against == "Project":
		budget.project = "_Test Project"
	else:
		budget.cost_center =cost_center or "_Test Cost Center - _TC"
	
	
	budget.fiscal_year = "_Test Fiscal Year 2013"
	budget.monthly_distribution = "_Test Distribution"
	budget.company = "_Test Company"
	budget.action_if_annual_budget_exceeded = "Stop"
	budget.action_if_accumulated_monthly_budget_exceeded = "Ignore"
	budget.budget_against = budget_against
	budget.append("accounts", {
		"account": "_Test Account Cost for Goods Sold - _TC",
		"budget_amount": 100000
	})
	
	budget.insert()
	budget.submit()

	return budget
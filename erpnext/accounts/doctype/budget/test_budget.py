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
		set_total_expense_zero("2013-02-28")

		budget = make_budget()
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv.name}))
			
		budget.cancel()

	def test_monthly_budget_crossed_stop(self):
		set_total_expense_zero("2013-02-28")

		budget = make_budget()
		
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.load_from_db()
		budget.cancel()

	def test_yearly_budget_crossed_stop(self):
		set_total_expense_zero("2013-02-28")

		budget = make_budget()
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 150000, "_Test Cost Center - _TC")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.cancel()

	def test_monthly_budget_on_cancellation(self):
		set_total_expense_zero("2013-02-28")

		budget = make_budget()
				
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
		
	def test_monthly_budget_against_group_cost_center(self):
		set_total_expense_zero("2013-02-28")
		set_total_expense_zero("2013-02-28", "_Test Cost Center 2 - _TC")
		
		budget = make_budget("_Test Company - _TC")
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center 2 - _TC")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.load_from_db()
		budget.cancel()

def set_total_expense_zero(posting_date, cost_center=None):
	existing_expense = get_actual_expense({
		"account": "_Test Account Cost for Goods Sold - _TC",
		"cost_center": cost_center or "_Test Cost Center - _TC",
		"monthly_end_date": posting_date,
		"company": "_Test Company",
		"fiscal_year": "_Test Fiscal Year 2013"
	}, cost_center or "_Test Cost Center - _TC")
	
	make_journal_entry("_Test Account Cost for Goods Sold - _TC",
		"_Test Bank - _TC", -existing_expense, "_Test Cost Center - _TC", submit=True)
		
def make_budget(cost_center=None):
	budget = frappe.new_doc("Budget")
	budget.cost_center = cost_center or "_Test Cost Center - _TC"
	budget.fiscal_year = "_Test Fiscal Year 2013"
	budget.monthly_distribution = "_Test Distribution"
	budget.company = "_Test Company"
	budget.action_if_annual_budget_exceeded = "Stop"
	budget.action_if_accumulated_monthly_budget_exceeded = "Ignore"
	
	budget.append("accounts", {
		"account": "_Test Account Cost for Goods Sold - _TC",
		"budget_amount": 100000
	})
	
	budget.insert()
	budget.submit()

	return budget
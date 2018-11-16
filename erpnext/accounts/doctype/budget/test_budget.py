# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate
from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.accounts.doctype.budget.budget import get_actual_expense, BudgetError
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

class TestBudget(unittest.TestCase):		
	def test_monthly_budget_crossed_ignore(self):
		set_total_expense_zero("2013-02-28", "Cost Center")

		budget = make_budget(budget_against="Cost Center")
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC", posting_date="2013-02-28", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv.name}))
			
		budget.cancel()

	def test_monthly_budget_crossed_stop1(self):
		set_total_expense_zero("2013-02-28", "Cost Center")

		budget = make_budget(budget_against="Cost Center")
		
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC", posting_date="2013-02-28")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.load_from_db()
		budget.cancel()

	def test_exception_approver_role(self):
		set_total_expense_zero("2013-02-28", "Cost Center")

		budget = make_budget(budget_against="Cost Center")

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
	
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC", posting_date="2013-03-02")

		self.assertRaises(BudgetError, jv.submit)

		frappe.db.set_value('Company', budget.company, 'exception_budget_approver_role', 'Accounts User')

		jv.submit()
		self.assertEqual(frappe.db.get_value('Journal Entry', jv.name, 'docstatus'), 1)
		jv.cancel()

		frappe.db.set_value('Company', budget.company, 'exception_budget_approver_role', '')

		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_crossed_for_mr(self):
		budget = make_budget(applicable_on_material_request=1,
			applicable_on_purchase_order=1, action_if_accumulated_monthly_budget_exceeded_on_mr="Stop",
			budget_against="Cost Center")

		fiscal_year = get_fiscal_year(nowdate())[0]
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
		frappe.db.set_value("Budget", budget.name, "fiscal_year", fiscal_year)

		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"transaction_date": nowdate(),
			"company": budget.company,
			"items": [{
				'item_code': '_Test Item',
				'qty': 1,
				'uom': "_Test UOM",
				'warehouse': '_Test Warehouse - _TC',
				'schedule_date': nowdate(),
				'rate': 100000,
				'expense_account': '_Test Account Cost for Goods Sold - _TC',
				'cost_center': '_Test Cost Center - _TC'
			}]
		})

		mr.set_missing_values()

		self.assertRaises(BudgetError, mr.submit)

		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_crossed_for_po(self):
		budget = make_budget(applicable_on_purchase_order=1,
			action_if_accumulated_monthly_budget_exceeded_on_po="Stop", budget_against="Cost Center")

		fiscal_year = get_fiscal_year(nowdate())[0]
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
		frappe.db.set_value("Budget", budget.name, "fiscal_year", fiscal_year)

		po = create_purchase_order(transaction_date=nowdate(), do_not_submit=True)

		po.set_missing_values()

		self.assertRaises(BudgetError, po.submit)

		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_crossed_stop2(self):
		set_total_expense_zero("2013-02-28", "Project")

		budget = make_budget(budget_against="Project")
		
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC", project="_Test Project", posting_date="2013-02-28")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.load_from_db()
		budget.cancel()

	def test_yearly_budget_crossed_stop1(self):
		set_total_expense_zero("2013-02-28", "Cost Center")

		budget = make_budget(budget_against="Cost Center")
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 150000, "_Test Cost Center - _TC", posting_date="2013-03-28")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.cancel()

	def test_yearly_budget_crossed_stop2(self):
		set_total_expense_zero("2013-02-28", "Project")

		budget = make_budget(budget_against="Project")
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 150000, "_Test Cost Center - _TC", project="_Test Project", posting_date="2013-03-28")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.cancel()

	def test_monthly_budget_on_cancellation1(self):
		set_total_expense_zero("2013-02-28", "Cost Center")

		budget = make_budget(budget_against="Cost Center")
				
		jv1 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", posting_date="2013-02-28", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv1.name}))

		jv2 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", posting_date="2013-02-28", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv2.name}))

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
		
		self.assertRaises(BudgetError, jv1.cancel)
		
		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_on_cancellation2(self):
		set_total_expense_zero("2013-02-28", "Project")

		budget = make_budget(budget_against="Project")
				
		jv1 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", posting_date="2013-02-28", submit=True, project="_Test Project")

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv1.name}))

		jv2 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", posting_date="2013-02-28", submit=True, project="_Test Project")

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv2.name}))

		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")
		
		self.assertRaises(BudgetError, jv1.cancel)
		
		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_against_group_cost_center(self):
		set_total_expense_zero("2013-02-28", "Cost Center")
		set_total_expense_zero("2013-02-28", "Cost Center", "_Test Cost Center 2 - _TC")
		
		budget = make_budget(budget_against="Cost Center", cost_center="_Test Company - _TC")
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center 2 - _TC", posting_date="2013-02-28")

		self.assertRaises(BudgetError, jv.submit)
		
		budget.load_from_db()
		budget.cancel()

	def test_monthly_budget_against_parent_group_cost_center(self):
		cost_center = "_Test Cost Center 3 - _TC"

		if not frappe.db.exists("Cost Center", cost_center):
			frappe.get_doc({
				'doctype': 'Cost Center',
				'cost_center_name': '_Test Cost Center 3',
				'parent_cost_center': "_Test Company - _TC",
				'company': '_Test Company',
				'is_group': 0
			}).insert(ignore_permissions=True)

		budget = make_budget(budget_against="Cost Center", cost_center=cost_center)
		frappe.db.set_value("Budget", budget.name, "action_if_accumulated_monthly_budget_exceeded", "Stop")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, cost_center, posting_date="2013-02-28")

		self.assertRaises(BudgetError, jv.submit)

		budget.load_from_db()
		budget.cancel()
		jv.cancel()

		frappe.delete_doc('Journal Entry', jv.name)
		frappe.delete_doc('Cost Center', cost_center)

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
			"_Test Bank - _TC", -existing_expense, "_Test Cost Center - _TC", posting_date="2013-02-28", submit=True)
		elif budget_against_field == "Project":
			make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", -existing_expense, "_Test Cost Center - _TC", submit=True, project="_Test Project", posting_date="2013-02-28")

def make_budget(**args):
	args = frappe._dict(args)

	budget_against=args.budget_against
	cost_center=args.cost_center

	if budget_against == "Project":
		budget_list = frappe.get_all("Budget", fields=["name"], filters = {"name": ("like", "_Test Project/_Test Fiscal Year 2013%")})
	else:
		cost_center_name = "{0}%".format(cost_center or "_Test Cost Center - _TC/_Test Fiscal Year 2013")
		budget_list = frappe.get_all("Budget", fields=["name"], filters = {"name": ("like", cost_center_name)})
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
	budget.applicable_on_booking_actual_expenses = 1
	budget.action_if_annual_budget_exceeded = "Stop"
	budget.action_if_accumulated_monthly_budget_exceeded = "Ignore"
	budget.budget_against = budget_against
	budget.append("accounts", {
		"account": "_Test Account Cost for Goods Sold - _TC",
		"budget_amount": 100000
	})
	
	if args.applicable_on_material_request:
		budget.applicable_on_material_request = 1
		budget.action_if_annual_budget_exceeded_on_mr = args.action_if_annual_budget_exceeded_on_mr or 'Warn'
		budget.action_if_accumulated_monthly_budget_exceeded_on_mr = args.action_if_accumulated_monthly_budget_exceeded_on_mr or 'Warn'

	if args.applicable_on_purchase_order:
		budget.applicable_on_purchase_order = 1
		budget.action_if_annual_budget_exceeded_on_po = args.action_if_annual_budget_exceeded_on_po or 'Warn'
		budget.action_if_accumulated_monthly_budget_exceeded_on_po = args.action_if_accumulated_monthly_budget_exceeded_on_po or 'Warn'

	budget.insert()
	budget.submit()

	return budget

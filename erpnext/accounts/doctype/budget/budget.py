# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, get_last_day
from frappe.model.naming import make_autoname
from frappe.model.document import Document

class BudgetError(frappe.ValidationError): pass

class Budget(Document):
	def autoname(self):
		self.name = make_autoname(self.cost_center + "/" + self.fiscal_year + "/.###")
		
	def validate(self):
		self.validate_duplicate()
		
	def validate_duplicate(self):
		existing_budget = frappe.db.get_value("Budget", {"cost_center": self.cost_center, 
			"fiscal_year": self.fiscal_year, "name": ["!=", self.name], "docstatus": ["!=", 2]})
		if existing_budget:
			frappe.throw(_("Another Budget record {0} already exists against {1} for fiscal year {2}")
				.format(existing_budget, self.cost_center, self.fiscal_year))


def validate_expense_against_budget(args):
	args = frappe._dict(args)
	if frappe.db.get_value("Account", {"name": args.account, "root_type": "Expense"}):
			budget = frappe.db.sql("""
				select ba.budget_amount, b.monthly_distribution, 
					b.action_if_annual_budget_exceeded, b.action_if_accumulated_monthly_budget_exceeded
				from `tabBudget` b, `tabBudget Account` ba
				where b.name=ba.parent and b.cost_center=%s and b.fiscal_year=%s and ba.account=%s
			""", (args.cost_center, args.fiscal_year, args.account), as_dict=True)
			
			if budget and budget[0].budget_amount:
				yearly_action = budget[0].action_if_annual_budget_exceeded
				monthly_action = budget[0].action_if_accumulated_monthly_budget_exceeded
				
				action_for = action = ""

				if monthly_action in ["Stop", "Warn"]:
					budget_amount = get_accumulated_monthly_budget(budget[0].monthly_distribution,
						args.posting_date, args.fiscal_year, budget[0].budget_amount)

					args["month_end_date"] = get_last_day(args.posting_date)
					
					action_for, action = _("Accumulated Monthly"), monthly_action

				elif yearly_action in ["Stop", "Warn"]:
					budget_amount = flt(budget[0].budget_amount)
					action_for, action = _("Annual"), yearly_action
				
				if action_for:
					actual_expense = get_actual_expense(args)
					if actual_expense > budget_amount:
						diff = actual_expense - budget_amount
						
						msg = _("{0} Budget for Account {1} against Cost Center {2} is {3}. It will exceed by {4}").format(_(action_for), args.account, args.cost_center, budget_amount, diff)
						
						if action=="Stop":
							frappe.throw(msg, BudgetError)
						else:
							frappe.msgprint(msg)

def get_accumulated_monthly_budget(monthly_distribution, posting_date, fiscal_year, annual_budget):
	distribution = {}
	if monthly_distribution:	
		for d in frappe.db.sql("""select mdp.month, mdp.percentage_allocation
			from `tabMonthly Distribution Percentage` mdp, `tabMonthly Distribution` md
			where mdp.parent=md.name and md.fiscal_year=%s""", fiscal_year, as_dict=1):
				distribution.setdefault(d.month, d.percentage_allocation)

	dt = frappe.db.get_value("Fiscal Year", fiscal_year, "year_start_date")
	accumulated_percentage = 0.0

	while(dt <= getdate(posting_date)):
		if monthly_distribution:
			accumulated_percentage += distribution.get(getdate(dt).strftime("%B"), 0)
		else:
			accumulated_percentage += 100.0/12

		dt = add_months(dt, 1)

	return annual_budget * accumulated_percentage / 100

def get_actual_expense(args):
	args["condition"] = " and posting_date <= '%s'" % \
		 args.month_end_date if args.get("month_end_date") else ""

	return flt(frappe.db.sql("""
		select sum(debit) - sum(credit)
		from `tabGL Entry`
		where account='%(account)s' and cost_center='%(cost_center)s'
		and fiscal_year='%(fiscal_year)s' and company='%(company)s' and docstatus=1 %(condition)s
	""" % (args))[0][0])
 # -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, get_last_day, fmt_money
from frappe.model.naming import make_autoname
from frappe.model.document import Document

class BudgetError(frappe.ValidationError): pass
class DuplicateBudgetError(frappe.ValidationError): pass

class Budget(Document):
	def autoname(self):
		self.name = make_autoname(self.get(frappe.scrub(self.budget_against)) 
			+ "/" + self.fiscal_year + "/.###")

	def validate(self):
		if not self.get(frappe.scrub(self.budget_against)):
			frappe.throw(_("{0} is mandatory").format(self.budget_against))
		self.validate_duplicate()
		self.validate_accounts()
		self.set_null_value()

	def validate_duplicate(self):
		budget_against_field = frappe.scrub(self.budget_against)
		budget_against = self.get(budget_against_field)
		existing_budget = frappe.db.get_value("Budget", {budget_against_field: budget_against,
			"fiscal_year": self.fiscal_year, "company": self.company,
			"name": ["!=", self.name], "docstatus": ["!=", 2]})
		if existing_budget: 
			frappe.throw(_("Another Budget record '{0}' already exists against {1} '{2}' for fiscal year {3}")
				.format(existing_budget, self.budget_against, budget_against, self.fiscal_year), DuplicateBudgetError)
	
	def validate_accounts(self):
		account_list = []
		for d in self.get('accounts'):
			if d.account:
				account_details = frappe.db.get_value("Account", d.account,
					["is_group", "company", "report_type"], as_dict=1)

				if account_details.is_group:
					frappe.throw(_("Budget cannot be assigned against Group Account {0}").format(d.account))
				elif account_details.company != self.company:
					frappe.throw(_("Account {0} does not belongs to company {1}")
						.format(d.account, self.company))
				elif account_details.report_type != "Profit and Loss":
					frappe.throw(_("Budget cannot be assigned against {0}, as it's not an Income or Expense account")
						.format(d.account))

				if d.account in account_list:
					frappe.throw(_("Account {0} has been entered multiple times").format(d.account))
				else:
					account_list.append(d.account)

	def set_null_value(self):
		if self.budget_against == 'Cost Center':
			self.project = None
		else:
			self.cost_center = None

def validate_expense_against_budget(args):
	args = frappe._dict(args)
	if not args.cost_center and not args.project:
		return
	for budget_against in ['project', 'cost_center']:
		if args.get(budget_against) \
				and frappe.db.get_value("Account", {"name": args.account, "root_type": "Expense"}):

			if args.project and budget_against == 'project':
				condition = "and b.project='%s'" % frappe.db.escape(args.project)
				args.budget_against_field = "Project"
			
			elif args.cost_center and budget_against == 'cost_center':
				cc_lft, cc_rgt = frappe.db.get_value("Cost Center", args.cost_center, ["lft", "rgt"])
				condition = """and exists(select name from `tabCost Center` 
					where lft<=%s and rgt>=%s and name=b.cost_center)""" % (cc_lft, cc_rgt)
				args.budget_against_field = "Cost Center"

			args.budget_against = args.get(budget_against)

			budget_records = frappe.db.sql("""
				select
					b.{budget_against_field}, ba.budget_amount, b.monthly_distribution,
					b.action_if_annual_budget_exceeded, 
					b.action_if_accumulated_monthly_budget_exceeded
				from 
					`tabBudget` b, `tabBudget Account` ba
				where
					b.name=ba.parent and b.fiscal_year=%s 
					and ba.account=%s and b.docstatus=1
					{condition}
			""".format(condition=condition, 
				budget_against_field=frappe.scrub(args.get("budget_against_field"))),
				(args.fiscal_year, args.account), as_dict=True)
				
			if budget_records:
				validate_budget_records(args, budget_records)

def validate_budget_records(args, budget_records):
	for budget in budget_records:
		if flt(budget.budget_amount):
			yearly_action = budget.action_if_annual_budget_exceeded
			monthly_action = budget.action_if_accumulated_monthly_budget_exceeded

			if monthly_action in ["Stop", "Warn"]:
				budget_amount = get_accumulated_monthly_budget(budget.monthly_distribution,
					args.posting_date, args.fiscal_year, budget.budget_amount)
				args["month_end_date"] = get_last_day(args.posting_date)

				compare_expense_with_budget(args, budget_amount, 
					_("Accumulated Monthly"), monthly_action)

			if yearly_action in ("Stop", "Warn") and monthly_action != "Stop" \
				and yearly_action != monthly_action:
				compare_expense_with_budget(args, flt(budget.budget_amount), 
						_("Annual"), yearly_action)


def compare_expense_with_budget(args, budget_amount, action_for, action):
	actual_expense = get_actual_expense(args)
	if actual_expense > budget_amount:
		diff = actual_expense - budget_amount
		currency = frappe.db.get_value('Company', args.company, 'default_currency')

		msg = _("{0} Budget for Account {1} against {2} {3} is {4}. It will exceed by {5}").format(
				_(action_for), frappe.bold(args.account), args.budget_against_field, 
				frappe.bold(args.budget_against), 
				frappe.bold(fmt_money(budget_amount, currency=currency)), 
				frappe.bold(fmt_money(diff, currency=currency)))

		if action=="Stop":
			frappe.throw(msg, BudgetError)
		else:
			frappe.msgprint(msg, indicator='orange')


def get_actual_expense(args):
	condition1 = " and gle.posting_date <= %(month_end_date)s" \
		if args.get("month_end_date") else ""
	if args.budget_against_field == "Cost Center":
		lft_rgt = frappe.db.get_value(args.budget_against_field, 
			args.budget_against, ["lft", "rgt"], as_dict=1)
		args.update(lft_rgt)
		condition2 = """and exists(select name from `tabCost Center` 
			where lft>=%(lft)s and rgt<=%(rgt)s and name=gle.cost_center)"""
	
	elif args.budget_against_field == "Project":
		condition2 = "and exists(select name from `tabProject` where name=gle.project)"

	return flt(frappe.db.sql("""
		select sum(gle.debit) - sum(gle.credit)
		from `tabGL Entry` gle
		where gle.account=%(account)s
			{condition1}
			and gle.fiscal_year=%(fiscal_year)s
			and gle.company=%(company)s
			and gle.docstatus=1
			{condition2}
	""".format(condition1=condition1, condition2=condition2), (args))[0][0])


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

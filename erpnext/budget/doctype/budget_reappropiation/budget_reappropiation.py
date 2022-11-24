# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe import _, msgprint, scrub
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, fmt_money, formatdate, get_link_to_form, nowdate
from erpnext.budget.doctype.budget.budget import validate_expense_against_budget

class BudgetReappropiation(Document):
	def validate(self):
		self.validate_budget()

	def on_submit(self):
		self.budget_check()
		self.budget_appropriate(cancel=False)

	def on_cancel(self):
		self.budget_appropriate(cancel=True)
	
	#Added by Thukten on 13th Sept, 2023
	def validate_budget(self):
		budget_against_field = frappe.scrub(self.budget_against)
		from_budget_against = self.from_cost_center if self.budget_against == "Cost Center" else self.from_project
		to_budget_against = self.to_cost_center if self.budget_against == "Cost Center" else self.to_project

		if not self.items:
			frappe.throw(_("Please provide Budget Head or Account to Appropriate budget"))

		for d in self.items:
			if d.from_account:
				from_budget_exist = frappe.db.sql(
						"""
						select
							b.name, ba.account from `tabBudget` b, `tabBudget Account` ba
						where
							ba.parent = b.name and b.docstatus = 1 and b.company = %s and %s=%s and
							b.fiscal_year=%s and ba.account =%s """
						% ("%s", budget_against_field, "%s", "%s", "%s"),
						(self.company, from_budget_against, self.fiscal_year, d.from_account),
						as_dict=1,
					)
				if not from_budget_exist:
					frappe.throw(
						_(
							"Budget record doesnot exists against {0} '{1}' and account '{2}' for fiscal year {3}"
						).format(self.budget_against, from_budget_against, d.from_account, self.fiscal_year),
					)
			if d.to_account:
				to_budget_exist = frappe.db.sql(
						"""
						select
							b.name, ba.account from `tabBudget` b, `tabBudget Account` ba
						where
							ba.parent = b.name and b.docstatus = 1 and b.company = %s and %s=%s and
							b.fiscal_year=%s and ba.account =%s """
						% ("%s", budget_against_field, "%s", "%s", "%s"),
						(self.company, to_budget_against, self.fiscal_year, d.to_account),
						as_dict=1,
					)
				if not to_budget_exist:
					frappe.throw(
						_(
							"Budget record doesnot exists against {0} '{1}' and account '{2}' for fiscal year {3}"
						).format(self.budget_against, to_budget_against, d.to_account, self.fiscal_year),
					)
	
	# Check the budget amount in the from cost center and account
	def budget_check(self):
		args = frappe._dict()
		args.budget_against = self.budget_against
		args.cost_center = self.from_cost_center if self.budget_against == "Cost Center" else None
		args.project = self.from_project if self.budget_against == "Project" else None
		args.posting_date = self.appropriation_on
		args.fiscal_year = self.fiscal_year
		args.company = self.company
		for a in self.get('items'):
			args.account = a.from_account
			args.amount = a.amount
		validate_expense_against_budget(args)

	# Added by Thukten on 13th September, 2022
	def budget_appropriate(self, cancel=False):
		if frappe.db.get_value("Fiscal Year", self.fiscal_year, "closed"):
			frappe.throw("Fiscal Year " + fiscal_year + " has already been closed")
		else:
			budget_against_field = frappe.scrub(self.budget_against)
			from_budget_against = self.from_cost_center if self.budget_against == "Cost Center" else self.from_project
			to_budget_against = self.to_cost_center if self.budget_against == "Cost Center" else self.to_project
			for d in self.items:
				if d.amount <= 0:
					frappe.throw("Budget appropiation Amount should be greater than 0 for record " + str(a.idx))
				from_account = frappe.db.sql(
						"""
						select
							ba.name, ba.account from `tabBudget` b, `tabBudget Account` ba
						where
							ba.parent = b.name and b.docstatus < 2 and b.company = %s and %s=%s and
							b.fiscal_year=%s and ba.account =%s """
						% ("%s", budget_against_field, "%s", "%s", "%s"),
						(self.company, from_budget_against, self.fiscal_year, d.from_account),
						as_dict=1,
					)
				if from_account:
					from_budget_account = frappe.get_doc("Budget Account", from_account[0].name)
			
					sent = flt(from_budget_account.budget_sent) + flt(d.amount)
					total = flt(from_budget_account.budget_amount) - flt(d.amount)
					if cancel:
						sent = flt(from_budget_account.budget_sent) - flt(d.amount)
						total = flt(from_budget_account.budget_amount) + flt(d.amount)
					from_budget_account.db_set("budget_sent", flt(sent,2))
					from_budget_account.db_set("budget_amount", flt(total,2))
				
				to_account = frappe.db.sql(
						"""
						select
							ba.name, ba.account from `tabBudget` b, `tabBudget Account` ba
						where
							ba.parent = b.name and b.docstatus < 2 and b.company = %s and %s=%s and
							b.fiscal_year=%s and ba.account =%s """
						% ("%s", budget_against_field, "%s", "%s", "%s"),
						(self.company, to_budget_against, self.fiscal_year, d.to_account),
						as_dict=1,
					)
				
				#Add in the To Account and Cost Center or project
				if to_account:
					to_budget_account = frappe.get_doc("Budget Account", to_account[0].name)
					
					received = flt(to_budget_account.budget_received) + flt(d.amount)
					total = flt(to_budget_account.budget_amount) + flt(d.amount)
					if cancel:
						received = flt(to_budget_account.budget_received) - flt(d.amount)
						total = flt(to_budget_account.budget_amount) - flt(d.amount)
					to_budget_account.db_set("budget_received", received)
					to_budget_account.db_set("budget_amount", total)

				app_details = frappe.new_doc("Reappropriation Details")
				app_details.budget_against = self.budget_against
				app_details.from_cost_center = self.from_cost_center if self.budget_against == "Cost Center" else ""
				app_details.to_cost_center = self.to_cost_center if self.budget_against == "Cost Center" else ""
				app_details.from_account = d.from_account
				app_details.to_account = d.to_account
				app_details.from_project = self.from_project if self.budget_against == "Project" else ""
				app_details.to_project = self.to_project if self.budget_against == "Project" else ""
				app_details.amount =flt(d.amount,2)
				app_details.posting_date = nowdate()
				app_details.reference = self.name
				app_details.company = self.company
				app_details.submit()

			#Delete the reappropriation details for record
			if cancel:
				frappe.db.sql("delete from `tabReappropriation Details` where reference=%s", self.name)

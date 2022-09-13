# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint, scrub
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, fmt_money, formatdate, get_link_to_form, nowdate

class SupplementaryBudget(Document):
	def validate(self):
		self.validate_budget()

	def on_submit(self):
		self.supplement_budget(cancel=False)

	def on_cancel(self):
		self.supplement_budget(cancel=True)

	#Added by Thukten on 13th Sept, 2023
	def validate_budget(self):
		budget_against_field = frappe.scrub(self.budget_against)
		budget_against = self.get(budget_against_field)
		if not self.items:
			frappe.throw(_("Please provide Budget Head or Account to supplement budget"))

		for d in self.items:
			budget_exist = frappe.db.sql(
					"""
					select
						b.name, ba.account from `tabBudget` b, `tabBudget Account` ba
					where
						ba.parent = b.name and b.docstatus = 1 and b.company = %s and %s=%s and
						b.fiscal_year=%s and ba.account =%s """
					% ("%s", budget_against_field, "%s", "%s", "%s"),
					(self.company, budget_against, self.fiscal_year, d.account),
					as_dict=1,
				)
			if not budget_exist:
				frappe.throw(
					_(
						"Budget record doesnot exists against {0} '{1}' and account '{2}' for fiscal year {3}"
					).format(self.budget_against, budget_against, d.account, self.fiscal_year),
				)

	# Written by Thukten to perform budget supplement, 13 Sept 2022
	def supplement_budget(self, cancel = False):
		if frappe.db.get_value("Fiscal Year", self.fiscal_year, "closed"):
			frappe.throw("Fiscal Year " + fiscal_year + " has already been closed")
		else:
			budget_against_field = frappe.scrub(self.budget_against)
			budget_against = self.get(budget_against_field)
			for d in self.items:
				if d.amount <= 0:
					frappe.throw("Budget Supplementary Amount should be greater than 0 for record " + str(a.idx))
				to_account = frappe.db.sql(
						"""
						select
							ba.name, ba.account from `tabBudget` b, `tabBudget Account` ba
						where
							ba.parent = b.name and b.docstatus < 2 and b.company = %s and %s=%s and
							b.fiscal_year=%s and ba.account =%s """
						% ("%s", budget_against_field, "%s", "%s", "%s"),
						(self.company, budget_against, self.fiscal_year, d.account),
						as_dict=1,
					)
				if to_account:
					to_budget_account = frappe.get_doc("Budget Account", to_account[0].name)
					if cancel:
						supplement = flt(to_budget_account.supplementary_budget) - flt(d.amount)
						total = flt(to_budget_account.budget_amount) - flt(d.amount)
						frappe.db.sql("delete from `tabSupplementary Details` where reference = %s", self.name)
					else:
						supplement = flt(to_budget_account.supplementary_budget) + flt(d.amount)
						total = flt(to_budget_account.budget_amount) + flt(d.amount)
						# Added for easy reporting purpose
						supp_details = frappe.new_doc("Supplementary Details")
						supp_details.budget_against = self.budget_against
						supp_details.cost_center = self.cost_center if self.budget_against == "Cost Center" else ""
						supp_details.project = self.project if self.budget_against == "Project" else ""
						supp_details.account = d.account
						supp_details.amount = flt(d.amount)
						supp_details.company = self.company
						supp_details.reference = self.name
						supp_details.posting_date = nowdate()
						supp_details.submit()
					
					to_budget_account.db_set("supplementary_budget", flt(supplement))
					to_budget_account.db_set("budget_amount", flt(total))
				else:
					frappe.throw(_(
									"Budget not set for account %s under %s %s. Please check initital budget allocations"
								 ).format(d.account,
								 		 self.budget_against, 
										budget_against)
								)

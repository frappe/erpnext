# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils import formatdate
from erpnext.controllers.trends import get_period_date_ranges, get_period_month_ranges

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	cost_centers = get_cost_centers(filters)
	period_month_ranges = get_period_month_ranges(filters["period"], filters["fiscal_year"])
	cam_map = get_cost_center_account_month_map(filters)

	data = []
	for cost_center in cost_centers:
		cost_center_items = cam_map.get(cost_center)
		if cost_center_items:
			for account, monthwise_data in cost_center_items.items():
				row = [cost_center, account]
				totals = [0, 0, 0]
				for relevant_months in period_month_ranges:
					period_data = [0, 0, 0]
					for month in relevant_months:
						month_data = monthwise_data.get(month, {})
						for i, fieldname in enumerate(["target", "actual", "variance"]):
							value = flt(month_data.get(fieldname))
							period_data[i] += value
							totals[i] += value
					period_data[2] = period_data[0] - period_data[1]
					row += period_data
				totals[2] = totals[0] - totals[1]
				row += totals
				data.append(row)

	return columns, data

def get_columns(filters):
	columns = [_(filters.get("budget_against")) + ":Link/%s:120"%(filters.get("budget_against")), _("Account") + ":Link/Account:120"]

	group_months = False if filters["period"] == "Monthly" else True

	for from_date, to_date in get_period_date_ranges(filters["period"], filters["fiscal_year"]):
		for label in [_("Target") + " (%s)", _("Actual") + " (%s)", _("Variance") + " (%s)"]:
			if group_months:
				label = label % (formatdate(from_date, format_string="MMM") + " - " + formatdate(to_date, format_string="MMM"))
			else:
				label = label % formatdate(from_date, format_string="MMM")

			columns.append(label+":Float:120")

	return columns + [_("Total Target") + ":Float:120", _("Total Actual") + ":Float:120",
		_("Total Variance") + ":Float:120"]
		
def get_cost_centers(filters):
	cond = "and 1=1"
	if filters.get("budget_against") == "Cost Center":
		cond = "order by lft"

	return frappe.db.sql_list("""select name from `tab{tab}` where company=%s 
		{cond}""".format(tab=filters.get("budget_against"), cond=cond), filters.get("company"))

#Get cost center & target details
def get_cost_center_target_details(filters):
	return frappe.db.sql("""
			select b.{budget_against} as budget_against, b.monthly_distribution, ba.account, ba.budget_amount
			from `tabBudget` b, `tabBudget Account` ba
			where b.name=ba.parent and b.docstatus = 1 and b.fiscal_year=%s
			and b.budget_against = %s and b.company=%s
		""".format(budget_against=filters.get("budget_against").replace(" ", "_").lower()),
		(filters.fiscal_year, filters.budget_against, filters.company), as_dict=True)

#Get target distribution details of accounts of cost center
def get_target_distribution_details(filters):
	target_details = {}
	for d in frappe.db.sql("""select md.name, mdp.month, mdp.percentage_allocation
		from `tabMonthly Distribution Percentage` mdp, `tabMonthly Distribution` md
		where mdp.parent=md.name and md.fiscal_year=%s""", (filters["fiscal_year"]), as_dict=1):
			target_details.setdefault(d.name, {}).setdefault(d.month, flt(d.percentage_allocation))

	return target_details

#Get actual details from gl entry
def get_actual_details(name, filters):
	cond = "1=1"
	budget_against=filters.get("budget_against").replace(" ", "_").lower()

	if filters.get("budget_against") == "Cost Center":
		cc_lft, cc_rgt = frappe.db.get_value("Cost Center", name, ["lft", "rgt"])
		cond = "lft>='{lft}' and rgt<='{rgt}'".format(lft = cc_lft, rgt=cc_rgt)
	
	ac_details = frappe.db.sql("""select gl.account, gl.debit, gl.credit,
		MONTHNAME(gl.posting_date) as month_name, b.{budget_against} as budget_against
		from `tabGL Entry` gl, `tabBudget Account` ba, `tabBudget` b
		where
			b.name = ba.parent
			and b.docstatus = 1
			and ba.account=gl.account 
			and gl.fiscal_year=%s 
			and b.{budget_against}=%s
			and exists(select name from `tab{tab}` where name=gl.{budget_against} and {cond})
	""".format(tab = filters.budget_against, budget_against = budget_against, cond = cond),
	(filters.fiscal_year, name), as_dict=1)

	cc_actual_details = {}
	for d in ac_details:
		cc_actual_details.setdefault(d.account, []).append(d)

	return cc_actual_details

def get_cost_center_account_month_map(filters):
	import datetime
	cost_center_target_details = get_cost_center_target_details(filters)
	tdd = get_target_distribution_details(filters)

	cam_map = {}

	for ccd in cost_center_target_details:
		actual_details = get_actual_details(ccd.budget_against, filters)
		
		for month_id in range(1, 13):
			month = datetime.date(2013, month_id, 1).strftime('%B')

			cam_map.setdefault(ccd.budget_against, {}).setdefault(ccd.account, {})\
				.setdefault(month, frappe._dict({
					"target": 0.0, "actual": 0.0
				}))

			tav_dict = cam_map[ccd.budget_against][ccd.account][month]
			month_percentage = tdd.get(ccd.monthly_distribution, {}).get(month, 0) \
				if ccd.monthly_distribution else 100.0/12

			tav_dict.target = flt(ccd.budget_amount) * month_percentage / 100
			
			for ad in actual_details.get(ccd.account, []):
				if ad.month_name == month:
						tav_dict.actual += flt(ad.debit) - flt(ad.credit)

	return cam_map

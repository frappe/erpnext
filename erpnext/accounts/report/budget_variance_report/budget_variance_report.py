# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils import formatdate
from erpnext.controllers.trends import get_period_date_ranges, get_period_month_ranges

from six import iteritems
from pprint import pprint
def execute(filters=None):
	if not filters: filters = {}
	validate_filters(filters)
	columns = get_columns(filters)
	if filters.get("cost_center"):
		cost_centers = [filters.get("cost_center")]
	else:
		cost_centers = get_cost_centers(filters)

	period_month_ranges = get_period_month_ranges(filters["period"], filters["from_fiscal_year"])
	cam_map = get_cost_center_account_month_map(filters)

	data = []
	for cost_center in cost_centers:
		cost_center_items = cam_map.get(cost_center)
		if cost_center_items:
			for account, monthwise_data in iteritems(cost_center_items):
				row = [cost_center, account]
				totals = [0, 0, 0]
				for year in get_fiscal_years(filters):
					last_total = 0
					for relevant_months in period_month_ranges:
						period_data = [0, 0, 0]
						for month in relevant_months:
							if monthwise_data.get(year[0]):
								month_data = monthwise_data.get(year[0]).get(month, {})
								for i, fieldname in enumerate(["target", "actual", "variance"]):
									value = flt(month_data.get(fieldname))
									period_data[i] += value
									totals[i] += value

						period_data[0] += last_total

						if(filters.get("show_cumulative")):
							last_total = period_data[0] - period_data[1]
						
						period_data[2] = period_data[0] - period_data[1] 
						row += period_data
				totals[2] = totals[0] - totals[1]
				if filters["period"] != "Yearly" :
					row += totals
				data.append(row)

	return columns, data

def validate_filters(filters):
	if filters.get("budget_against")=="Project" and filters.get("cost_center"):
		frappe.throw(_("Filter based on Cost Center is only applicable if Budget Against is selected as Cost Center"))

def get_columns(filters):
	columns = [_(filters.get("budget_against")) + ":Link/%s:80"%(filters.get("budget_against")), _("Account") + ":Link/Account:80"]

	group_months = False if filters["period"] == "Monthly" else True

	fiscal_year = get_fiscal_years(filters)

	for year in fiscal_year:
		for from_date, to_date in get_period_date_ranges(filters["period"], year[0]):
			if filters["period"] == "Yearly":
				labels = [_("Budget") + " " + str(year[0]), _("Actual ") + " " + str(year[0]), _("Varaiance ") + " " + str(year[0])]
				for label in labels:
					columns.append(label+":Float:80")
			else:
				for label in [_("Budget") + " (%s)" + " " + str(year[0]), _("Actual") + " (%s)" + " " + str(year[0]), _("Variance") + " (%s)" + " " + str(year[0])]:
					if group_months:
						label = label % (formatdate(from_date, format_string="MMM") + "-" + formatdate(to_date, format_string="MMM"))
					else:
						label = label % formatdate(from_date, format_string="MMM")

					columns.append(label+":Float:80")

	if filters["period"] != "Yearly" :
		return columns + [_("Total Budget") + ":Float:80", _("Total Actual") + ":Float:80",
			_("Total Variance") + ":Float:80"]
	else:
		return columns

def get_cost_centers(filters):
	cond = "and 1=1"
	if filters.get("budget_against") == "Cost Center":
		cond = "order by lft"

	return frappe.db.sql_list("""select name from `tab{tab}` where company=%s
		{cond}""".format(tab=filters.get("budget_against"), cond=cond), filters.get("company"))

#Get cost center & target details
def get_cost_center_target_details(filters):
	cond = ""
	if filters.get("cost_center"):
		cond += " and b.cost_center=%s" % frappe.db.escape(filters.get("cost_center"))

	return frappe.db.sql("""
			select b.{budget_against} as budget_against, b.monthly_distribution, ba.account, ba.budget_amount,b.fiscal_year
			from `tabBudget` b, `tabBudget Account` ba
			where b.name=ba.parent and b.docstatus = 1 and b.fiscal_year between %s and %s
			and b.budget_against = %s and b.company=%s {cond} order by b.fiscal_year
		""".format(budget_against=filters.get("budget_against").replace(" ", "_").lower(), cond=cond),
		(filters.from_fiscal_year,filters.to_fiscal_year,filters.budget_against, filters.company), as_dict=True)

	

#Get target distribution details of accounts of cost center
def get_target_distribution_details(filters):
	target_details = {}
	for d in frappe.db.sql("""select md.name, mdp.month, mdp.percentage_allocation
		from `tabMonthly Distribution Percentage` mdp, `tabMonthly Distribution` md
		where mdp.parent=md.name and md.fiscal_year between %s and %s order by md.fiscal_year""",(filters.from_fiscal_year, filters.to_fiscal_year), as_dict=1):
			target_details.setdefault(d.name, {}).setdefault(d.month, flt(d.percentage_allocation))
	
	return target_details

#Get actual details from gl entry
def get_actual_details(name, filters):
	cond = "1=1"
	budget_against=filters.get("budget_against").replace(" ", "_").lower()

	if filters.get("budget_against") == "Cost Center":
		cc_lft, cc_rgt = frappe.db.get_value("Cost Center", name, ["lft", "rgt"])
		cond = "lft>='{lft}' and rgt<='{rgt}'".format(lft = cc_lft, rgt=cc_rgt)
	
	ac_details = frappe.db.sql("""select gl.account, gl.debit, gl.credit,gl.fiscal_year,
		MONTHNAME(gl.posting_date) as month_name, b.{budget_against} as budget_against
		from `tabGL Entry` gl, `tabBudget Account` ba, `tabBudget` b
		where
			b.name = ba.parent
			and b.docstatus = 1
			and ba.account=gl.account
			and b.{budget_against} = gl.{budget_against}
			and gl.fiscal_year between %s and %s
			and b.{budget_against}=%s
			and exists(select name from `tab{tab}` where name=gl.{budget_against} and {cond}) group by gl.name order by gl.fiscal_year
	""".format(tab = filters.budget_against, budget_against = budget_against, cond = cond,from_year=filters.from_fiscal_year,to_year=filters.to_fiscal_year),
	(filters.from_fiscal_year, filters.to_fiscal_year, name), as_dict=1)

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
			cam_map.setdefault(ccd.budget_against, {}).setdefault(ccd.account, {}).setdefault(ccd.fiscal_year,{})\
				.setdefault(month, frappe._dict({
					"target": 0.0, "actual": 0.0
				}))

			tav_dict = cam_map[ccd.budget_against][ccd.account][ccd.fiscal_year][month]
			month_percentage = tdd.get(ccd.monthly_distribution, {}).get(month, 0) \
				if ccd.monthly_distribution else 100.0/12

			tav_dict.target = flt(ccd.budget_amount) * month_percentage / 100

			for ad in actual_details.get(ccd.account, []):
				if ad.month_name == month:
						tav_dict.actual += flt(ad.debit) - flt(ad.credit)

	return cam_map

def get_fiscal_years(filters):

	fiscal_year = frappe.db.sql("""select name from `tabFiscal Year` where
	name between %(from_fiscal_year)s and %(to_fiscal_year)s""",
	{'from_fiscal_year': filters["from_fiscal_year"], 'to_fiscal_year': filters["to_fiscal_year"]})

	return fiscal_year

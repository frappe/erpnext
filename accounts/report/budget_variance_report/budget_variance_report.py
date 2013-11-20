# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
from webnotes.utils import flt
import time
from accounts.utils import get_fiscal_year
from controllers.trends import get_period_date_ranges, get_period_month_ranges

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns(filters)
	period_month_ranges = get_period_month_ranges(filters["period"], filters["fiscal_year"])
	cam_map = get_costcenter_account_month_map(filters)

	data = []
	for cost_center, cost_center_items in cam_map.items():
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

	return columns, sorted(data, key=lambda x: (x[0], x[1]))
	
def get_columns(filters):
	for fieldname in ["fiscal_year", "period", "company"]:
		if not filters.get(fieldname):
			label = (" ".join(fieldname.split("_"))).title()
			msgprint(_("Please specify") + ": " + label,
				raise_exception=True)

	columns = ["Cost Center:Link/Cost Center:120", "Account:Link/Account:120"]

	group_months = False if filters["period"] == "Monthly" else True

	for from_date, to_date in get_period_date_ranges(filters["period"], filters["fiscal_year"]):
		for label in ["Target (%s)", "Actual (%s)", "Variance (%s)"]:
			if group_months:
				label = label % (from_date.strftime("%b") + " - " + to_date.strftime("%b"))
			else:
				label = label % from_date.strftime("%b")
				
			columns.append(label+":Float:120")

	return columns + ["Total Target:Float:120", "Total Actual:Float:120", 
		"Total Variance:Float:120"]

#Get cost center & target details
def get_costcenter_target_details(filters):
	return webnotes.conn.sql("""select cc.name, cc.distribution_id, 
		cc.parent_cost_center, bd.account, bd.budget_allocated 
		from `tabCost Center` cc, `tabBudget Detail` bd 
		where bd.parent=cc.name and bd.fiscal_year=%s and 
		cc.company=%s order by cc.name""" % ('%s', '%s'), 
		(filters.get("fiscal_year"), filters.get("company")), as_dict=1)

#Get target distribution details of accounts of cost center
def get_target_distribution_details(filters):
	target_details = {}

	for d in webnotes.conn.sql("""select bd.name, bdd.month, bdd.percentage_allocation \
		from `tabBudget Distribution Detail` bdd, `tabBudget Distribution` bd
		where bdd.parent=bd.name and bd.fiscal_year=%s""", (filters["fiscal_year"]), as_dict=1):
			target_details.setdefault(d.name, {}).setdefault(d.month, d.percentage_allocation)

	return target_details

#Get actual details from gl entry
def get_actual_details(filters):
	ac_details = webnotes.conn.sql("""select gl.account, gl.debit, gl.credit, 
		gl.cost_center, MONTHNAME(gl.posting_date) as month_name 
		from `tabGL Entry` gl, `tabBudget Detail` bd 
		where gl.fiscal_year=%s and company=%s
		and bd.account=gl.account and bd.parent=gl.cost_center""" % ('%s', '%s'), 
		(filters.get("fiscal_year"), filters.get("company")), as_dict=1)
		
	cc_actual_details = {}
	for d in ac_details:
		cc_actual_details.setdefault(d.cost_center, {}).setdefault(d.account, []).append(d)
		
	return cc_actual_details

def get_costcenter_account_month_map(filters):
	import datetime
	costcenter_target_details = get_costcenter_target_details(filters)
	tdd = get_target_distribution_details(filters)
	actual_details = get_actual_details(filters)

	cam_map = {}

	for ccd in costcenter_target_details:
		for month_id in range(1, 13):
			month = datetime.date(2013, month_id, 1).strftime('%B')
			
			cam_map.setdefault(ccd.name, {}).setdefault(ccd.account, {})\
				.setdefault(month, webnotes._dict({
					"target": 0.0, "actual": 0.0
				}))

			tav_dict = cam_map[ccd.name][ccd.account][month]
			month_percentage = ccd.distribution_id and \
				tdd.get(ccd.distribution_id, {}).get(month, 0) or 100.0/12
				
			tav_dict.target = flt(ccd.budget_allocated) * month_percentage /100
			
			for ad in actual_details.get(ccd.name, {}).get(ccd.account, []):
				if ad.month_name == month:
						tav_dict.actual += ad.debit - ad.credit
						
	return cam_map
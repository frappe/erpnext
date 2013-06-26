# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

	precision = webnotes.conn.get_value("Global Defaults", None, "float_precision") or 2

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
						value = flt(month_data.get(fieldname), precision)
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

	columns = ["Cost Center:Link/Cost Center:100", "Account:Link/Account:100"]

	group_months = False if filters["period"] == "Monthly" else True

	for from_date, to_date in get_period_date_ranges(filters["period"], filters["fiscal_year"]):
		for label in ["Target (%s)", "Actual (%s)", "Variance (%s)"]:
			if group_months:
				columns.append(label % (from_date.strftime("%b") + " - " + to_date.strftime("%b")))				
			else:
				columns.append(label % from_date.strftime("%b"))

	return columns + ["Total Target::80", "Total Actual::80", "Total Variance::80"]

#Get cost center & target details
def get_costcenter_target_details(filters):
	return webnotes.conn.sql("""select cc.name, cc.distribution_id, 
		cc.parent_cost_center, bd.account, bd.budget_allocated 
		from `tabCost Center` cc, `tabBudget Detail` bd 
		where bd.parent=cc.name and bd.fiscal_year=%s and 
		cc.company_name=%s and ifnull(cc.distribution_id, '')!='' 
		order by cc.name""" % ('%s', '%s'), 
		(filters.get("fiscal_year"), filters.get("company")), as_dict=1)

#Get target distribution details of accounts of cost center
def get_target_distribution_details(filters):
	target_details = {}

	for d in webnotes.conn.sql("""select bdd.month, bdd.percentage_allocation \
		from `tabBudget Distribution Detail` bdd, `tabBudget Distribution` bd, \
		`tabCost Center` cc where bdd.parent=bd.name and cc.distribution_id=bd.name and \
		bd.fiscal_year=%s""", (filters["fiscal_year"]), as_dict=1):
			target_details.setdefault(d.month, d)

	return target_details

#Get actual details from gl entry
def get_actual_details(filters):
	return webnotes.conn.sql("""select gl.account, gl.debit, gl.credit, 
		gl.cost_center, MONTHNAME(gl.posting_date) as month_name 
		from `tabGL Entry` gl, `tabBudget Detail` bd 
		where gl.fiscal_year=%s and company=%s and	is_cancelled='No' 
		and bd.account=gl.account""" % ('%s', '%s'), 
		(filters.get("fiscal_year"), filters.get("company")), as_dict=1)

def get_costcenter_account_month_map(filters):
	costcenter_target_details = get_costcenter_target_details(filters)
	tdd = get_target_distribution_details(filters)
	actual_details = get_actual_details(filters)

	cam_map = {}

	for ccd in costcenter_target_details:
		for month in tdd:
			cam_map.setdefault(ccd.name, {}).setdefault(ccd.account, {})\
			.setdefault(month, webnotes._dict({
				"target": 0.0, "actual": 0.0
			}))

			tav_dict = cam_map[ccd.name][ccd.account][month]
			tav_dict.target = flt(ccd.budget_allocated) * \
				(tdd[month]["percentage_allocation"]/100)

			for ad in actual_details:
				if ad.month_name == month and ad.account == ccd.account \
					and ad.cost_center == ccd.name:
						tav_dict.actual += ad.debit - ad.credit
						
	return cam_map
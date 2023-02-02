# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from erpnext.accounts.accounts_custom_functions import get_child_cost_centers,get_period_date
from frappe.utils import flt, rounded, cint
from erpnext.custom_utils import get_production_groups
from erpnext.production.doctype.production_target.production_target import get_target_value

def execute(filters=None):
	build_filters(filters)
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def build_filters(filters):
	filters.is_company = frappe.db.get_value("Cost Center", filters.cost_center, "is_company")
	filters.from_date, filters.to_date = get_period_date(filters.fiscal_year, filters.report_period, filters.cumulative)
	
def get_data(filters):
	data = []
	cc_condition = get_cc_conditions(filters)
	conditions = get_filter_conditions(filters)

	group_by = get_group_by(filters)
	order_by = get_order_by(filters)
	abbr = " - " + str(frappe.db.get_value("Company", filters.company, "abbr"))

	query = """select pe.cost_center, 
				pe.branch, pe.location, 
				cc.parent_cost_center as region 
			from `tabProduction Target` pe, 
			`tabCost Center` cc 
			where cc.name = pe.cost_center 
			and pe.fiscal_year = {0} {1} {2} {3}""".format(filters.fiscal_year, cc_condition, group_by, order_by)
	for a in frappe.db.sql(query, as_dict=1):
		if filters.branch:
			target = get_target_value("Production", a.location, filters.production_group, filters.fiscal_year, filters.from_date, filters.to_date, True)
			row = [a.location, target]
			cond = " and location = '{0}'".format(a.location)
		else:
			if filters.is_company:
				target = get_target_value("Production", a.region, filters.production_group, filters.fiscal_year, filters.from_date, filters.to_date)
				all_ccs = get_child_cost_centers(a.region)
				cond = " and cost_center in {0} ".format(tuple(all_ccs))	
				a.region = str(a.region).replace(abbr, "")
				row = [a.region, target]
			else:
				target = get_target_value("Production", a.cost_center, filters.production_group, filters.fiscal_year, filters.from_date, filters.to_date)
				row = [a.branch, target]
				cond = " and cost_center = '{0}'".format(a.cost_center)
	
		total = 0
		# for b in get_production_groups(filters.production_group):
		qty = frappe.db.sql("select sum(pe.qty) from `tabProduction Entry` pe where 1 = 1 {0} and pe.item_code = '{1}' {2}".format(conditions, filters.production_group, cond))
		qty = qty and qty[0][0] or 0
		row.append(rounded(qty, 2))
		total += flt(qty)
		row.insert(2, rounded(total, 2))
		if target == 0:
			target = 1
		row.insert(3, rounded(100 * total/target, 2))
		data.append(row)

	return data

def get_group_by(filters):
	if filters.branch:
		group_by = " group by branch, location"
	else:
		if filters.is_company:
			group_by = " group by region"
		else:
			group_by = " group by branch"

	return group_by

def get_order_by(filters):
	return " order by branch, location"

def get_cc_conditions(filters):
	if not filters.cost_center:
		return " and pe.docstatus = 1"
	if cint(frappe.db.get_value("Cost Center",filters.cost_center,"is_group")) == 0:
		condition = " and cc.name = '{0}' ".format(filters.cost_center)
	else:
		all_ccs = get_child_cost_centers(filters.cost_center)
		condition = " and cc.name in {0} ".format(tuple(all_ccs))	
	return condition

def get_filter_conditions(filters):
	condition = ""
	if filters.location:
		condition += " and pe.location = '{0}'".format(filters.location)

	if filters.from_date and filters.to_date:
		condition += " and DATE(pe.posting_date) between '{0}' and '{1}'".format(filters.from_date, filters.to_date)

	return condition

def get_columns(filters):
	if filters.branch:
		columns = ["Location:Link/Location:150", "Target Qty:Float:120", "Achieved Qty:Float:120", "Ach. Percent:Percent:100"]
	else:
		if filters.is_company:
			columns = ["Region:150", "Target Qty:Float:120", "Achieved Qty:Float:120", "Ach. Percent:Percent:100"]
		else:
			columns = ["Branch:Link/Branch:150", "Target Qty:Float:120", "Achieved Qty:Float:120", "Ach. Percent:Percent:100"]

	if filters.production_group:
		columns.append(str(str(frappe.db.get_value("Item", filters.production_group, "item_name")) + ":Float:100"))
	
	return columns


# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.accounts_custom_functions import get_child_cost_centers,get_period_date
from frappe.utils import flt, rounded, cint
from erpnext.custom_utils import get_production_groups
from erpnext.accounts.doctype.sales_target.sales_target import get_target_value

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
	# conditions = get_filter_conditions(filters)
	group_by = get_group_by(filters)
	order_by = get_order_by(filters)
	abbr = " - " + str(frappe.db.get_value("Company", filters.company, "abbr"))

	query = """select pe.cost_center, 
				pe.branch, pe.item, 
				cc.parent_cost_center as region 
			from `tabSales Target` pe, 
			`tabCost Center` cc 
			where cc.name = pe.cost_center 
			and pe.fiscal_year = {0} {1} {2} {3}""".format(filters.fiscal_year, cc_condition, group_by, order_by)
	for a in frappe.db.sql(query, as_dict=1):
		if filters.branch:
			target = get_target_value("Sales", a.item,filters.fiscal_year, filters.from_date, filters.to_date, a.region)
			row = [a.item, target]
			cond = " and item = '{0}'".format(a.item)
	
		total = 0
		qty = frappe.db.sql("select sum(pe.qty) from `tabSales Invoice Item` pe, `tabSales Invoice` si where pe.parent = si.name and si.docstatus = 1 and pe.item_code = '{0}' and si.posting_date between '{1}' and '{2}'".format(filters.item, filters.from_date, filters.to_date))
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
		group_by = " group by branch, item"
	else:
		if filters.is_company:
			group_by = " group by region"
		else:
			group_by = " group by branch, item"
	return group_by

def get_order_by(filters):
	return " order by branch, item"

def get_cc_conditions(filters):
	if not filters.cost_center:
		return " and pe.docstatus = 1"
	if filters.item:
		condition = " and pe.item = {}".format(filters.item)
	return condition
	

def get_columns(filters):
	if filters.branch:
		columns = ["Item:Link/Item:150", "Target Qty:Float:120", "Achieved Qty:Float:120", "Ach. Percent:Percent:100"]
	else:
		if filters.is_company:
			columns = ["Region:150", "Target Qty:Float:120", "Achieved Qty:Float:120", "Ach. Percent:Percent:100"]
		else:
			columns = ["Branch:Link/Branch:150", "Target Qty:Float:120", "Achieved Qty:Float:120", "Ach. Percent:Percent:100"]

	if filters.production_group:
		columns.append(str(str(frappe.db.get_value("Item", filters.production_group, "item_name")) + ":Float:100"))
	
	return columns

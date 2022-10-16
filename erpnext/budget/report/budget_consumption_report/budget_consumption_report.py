# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr

def execute(filters=None):
	validate_filters(filters)
	columns = get_columns(filters)
	queries = construct_query(filters)
	data = get_data(queries, filters)
	return columns, data

def get_data(query, filters):
	data = []
	datas = frappe.db.sql(query, as_dict=True)
	ini = su = cur = cm = co = ad = av = 0
	budget_level = filters.budget_against
	for d in datas:
		if filters.group_by_account and filters.budget_against != "Project":
			cost_center = ""
			committed = frappe.db.sql("select SUM(amount) from `tabCommitted Budget` where account = %s and reference_date BETWEEN %s and %s", (d.account, filters.from_date, filters.to_date))[0][0]
			consumed = frappe.db.sql("select SUM(amount) from `tabConsumed Budget` where account = %s and reference_date BETWEEN %s and %s", (d.account, filters.from_date, filters.to_date))[0][0]
		elif filters.budget_against == "Project":
			project = filters.project
			committed = frappe.db.sql("select SUM(amount) from `tabCommitted Budget` where cost_center = %s and project = %s and reference_date BETWEEN %s and %s", (d.cost_center, d.project, filters.from_date, filters.to_date))[0][0]
			consumed = frappe.db.sql("select SUM(amount) from `tabConsumed Budget` where cost_center = %s and project = %s and reference_date BETWEEN %s and %s", (d.cost_center, d.project, filters.from_date, filters.to_date))[0][0]
		else:
			cost_center = d.cost_center
			committed = frappe.db.sql("select SUM(amount) from `tabCommitted Budget` where cost_center = %s and account = %s and reference_date BETWEEN %s and %s", (d.cost_center, d.account, filters.from_date, filters.to_date))[0][0]
			consumed = frappe.db.sql("select SUM(amount) from `tabConsumed Budget` where cost_center = %s and account = %s and reference_date BETWEEN %s and %s", (d.cost_center, d.account, filters.from_date, filters.to_date))[0][0]
		
		if not committed:
			committed = 0
		if not consumed:
			consumed = 0
			
		adjustment = flt(d.added) - flt(d.deducted)
		supplement = flt(d.supplement)
		current    = flt(d.initial_budget) + flt(d.supplement) +flt(adjustment)
		
		if committed > 0:
			committed -= consumed
			committed = 0 if committed < 0 else committed
				
		available = flt(d.initial_budget) + flt(adjustment) + flt(d.supplement) - flt(consumed) - flt(committed)
		if d.budget_amount > 0:
			if filters.budget_against != "Project":
				row = {
					"account": d.account,
					"account_number": d.account_number,
					"budget_type": d.budget_type,
					"cost_center": cost_center,
					"initial": flt(d.initial_budget),
					"supplementary": supplement,
					"adjustment": adjustment,
					"current": current,
					"committed": committed,
					"consumed": consumed,
					"available": available
				}
			else:
				row = {
					"account": d.account,
					"project": d.project,
					"project_name": d.project_name,
					"cost_center": d.cost_center,
					"initial": flt(d.initial_budget),
					"supplementary": supplement,
					"adjustment": adjustment,
					"current": current,
					"committed": committed,
					"consumed": consumed,
					"available": available
				}

			data.append(row)
			ini+=flt(d.initial_budget)
			su+=supplement
			cm+=committed
			cur+=current
			co+=consumed
			ad+=adjustment
			av+=available
	row = {
		"account": "Total",
		"cost_center": "",
		"initial": ini,
		"supplementary": su,
		"adjustment": ad,
		"curernt":cur,
		"committed": cm,
		"consumed": co,
		"available": av
	}
	data.append(row)
	return data

def construct_query(filters=None):
	if filters.budget_against == "Project" and filters.project:
		condition += " and b.project = \'" + str(filters.project) + "\' "
	else:
		condition += " and b.cost_center = \'" + str(filters.cost_center) + "\' "
	
	if filters.budget_type:
		condition += " and ba.budget_type = \'" + str(filters.budget_type) + "\' "
	
	if filters.cost_center and not filters.group_by_account:
		lft, rgt = frappe.db.get_value("Cost Center", filters.cost_center, ["lft", "rgt"])
		condition += """ and (b.cost_center in (select a.name 
											from `tabCost Center` a 
											where a.lft >= {1} and a.rgt <= {2}
											) 
					 or b.cost_center = '{0}')
				""".format(filters.cost_center, lft, rgt)
	if filters.budget_type:
		condition += " and ba.budget_type = \'" + str(filters.budget_type) + "\' "

	query = """select b.cost_center, ba.account, b.project,
			(select a.account_number from `tabAccount` a where a.name = ba.account) as account_number, 
			ba.budget_type,
			SUM(ba.budget_amount) as budget_amount, 
			SUM(ba.initial_budget) as initial_budget, 
			SUM(ba.budget_received) as added, 
			SUM(ba.budget_sent) as deducted, 
			SUM(ba.supplementary_budget) as supplement
		from `tabBudget` b, `tabBudget Account` ba 
		where b.docstatus = 1 
			and b.name = ba.parent 
			and b.fiscal_year = {fiscal_year}
		{condition}
		""".format(fiscal_year=filters.fiscal_year, condition=condition)

	if filters.group_by_account:
		query += " group by ba.account "
	elif filters.budget_against == "Project":
		query += " group by b.cost_center, b.project"
	else:
		query += " group by ba.account, b.cost_center order by b.cost_center"
	return query

def validate_filters(filters):
	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))

	fiscal_year = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True)
	if not fiscal_year:
		frappe.throw(_("Fiscal Year {0} does not exist").format(filters.fiscal_year))
	else:
		filters.year_start_date = getdate(fiscal_year.year_start_date)
		filters.year_end_date = getdate(fiscal_year.year_end_date)

	if not filters.from_date:
		filters.from_date = filters.year_start_date

	if not filters.to_date:
		filters.to_date = filters.year_end_date

	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	if (filters.from_date < filters.year_start_date) or (filters.from_date > filters.year_end_date):
		frappe.msgprint(_("From Date should be within the Fiscal Year. Assuming From Date = {0}")\
			.format(formatdate(filters.year_start_date)))

		filters.from_date = filters.year_start_date

	if (filters.to_date < filters.year_start_date) or (filters.to_date > filters.year_end_date):
		frappe.msgprint(_("To Date should be within the Fiscal Year. Assuming To Date = {0}")\
			.format(formatdate(filters.year_end_date)))
		filters.to_date = filters.year_end_date

def construct_query(filters=None):
	query = """select 
			b.cost_center, ba.account, b.project, b.project_name,
			(select a.account_number from `tabAccount` a where a.name = ba.account) as account_number, 
			ba.budget_type,
			SUM(ba.budget_amount) as budget_amount, 
			SUM(ba.initial_budget) as initial_budget, 
			SUM(ba.budget_received) as added, 
			SUM(ba.budget_sent) as deducted, 
			SUM(ba.supplementary_budget) as supplement
		from `tabBudget` b, `tabBudget Account` ba 
		where b.docstatus = 1 
		and b.name = ba.parent 
		and b.fiscal_year = """ + str(filters.fiscal_year)
	if filters.budget_against == "Cost Center" and filters.cost_center and not filters.group_by_account:
		lft, rgt = frappe.db.get_value("Cost Center", filters.cost_center, ["lft", "rgt"])
		query += " and (b.cost_center in (select a.name from `tabCost Center` a where a.lft >= {1} and a.rgt <= {2}) or b.cost_center = '{0}')".format(filters.cost_center, lft, rgt)
	
	if filters.budget_against == "Project":
		query += " and b.project = \'" + str(filters.project) + "\' "

	if filters.budget_type:
		query += " and ba.budget_type = \'" + str(filters.budget_type) + "\' "

	if filters.group_by_account:
		query += " group by ba.account order by ba.account"
	elif filters.budget_against == "Project":
		query += " group by b.cost_center, b.project"
	else:
		query += " group by ba.account, b.cost_center order by b.cost_center"
	return query

def get_columns(filters):
	if filters.budget_against == "Project":
		return [
			{
				"fieldname": "account",
				"label": "Account Head",
				"fieldtype": "Link",
				"options": "Account",
				"width": 200
			},
			{
				"fieldname": "project",
				"label": "Project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 120
			},
			{
				"fieldname": "project_name",
				"label": "Project Name",
				"fieldtype": "Data",
				"width": 120
			},
			{
				"fieldname": "cost_center",
				"label": "Cost Center",
				"fieldtype": "Link",
				"options": "Cost Center",
				"width": 150
			},
			{
				"fieldname": "initial",
				"label": "Initial",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "supplementary",
				"label": "Supplement",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"fieldname": "adjustment",
				"label": "Adjustment",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "current",
				"label": "Current",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "committed",
				"label": "Committed",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "consumed",
				"label": "Consumed",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "available",
				"label": "Available",
				"fieldtype": "Currency",
				"width": 120
			}
		]
	else:
		return [
			{
				"fieldname": "account",
				"label": "Account Head",
				"fieldtype": "Link",
				"options": "Account",
				"width": 200
			},
			{
				"fieldname": "account_number",
				"label": "Account Number",
				"fieldtype": "Data",
				"width": 120
			},
			{
				"fieldname": "budget_type",
				"label": "Budget Type",
				"fieldtype": "Link",
				"options": "Budget Type",
				"width": 120,
			},
			{
				"fieldname": "cost_center",
				"label": "Cost Center",
				"fieldtype": "Link",
				"options": "Cost Center",
				"width": 150
			},
			{
				"fieldname": "initial",
				"label": "Initial",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "supplementary",
				"label": "Supplement",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"fieldname": "adjustment",
				"label": "Adjustment",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "current",
				"label": "Current",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "committed",
				"label": "Committed",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "consumed",
				"label": "Consumed",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "available",
				"label": "Available",
				"fieldtype": "Currency",
				"width": 120
			}
		]
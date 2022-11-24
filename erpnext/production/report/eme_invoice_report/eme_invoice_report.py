# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)
from frappe.utils import cstr, cint, flt, getdate, add_days, formatdate
from frappe import msgprint, _, qb, throw, bold

def execute(filters=None):
	period_list = get_period_list(
			filters.fiscal_year, 
			filters.fiscal_year, 
			period_start_date = getdate(str(filters.fiscal_year + '-01-01')),
			period_end_date = getdate(str(filters.fiscal_year + '-12-31')),
			filter_based_on = filters.filter_based_on,
			periodicity = filters.periodicity,
			company=filters.company)
	
	if filters.purpose == 'Expense Account and Expense Head':
		columns = get_columns_expense_account(filters.periodicity, period_list, filters.accumulated_values)
		data = get_data_expense_account(filters, period_list)
		return columns, data
	else:
		columns = get_columns_expense_head(filters.periodicity, period_list, filters.accumulated_values)
		data = get_data_expense_head(filters, period_list)
		return columns, data

#====================================================================================================
# The functions below collects data and columns when the purpose is Expense Account and Expense Head 
#====================================================================================================

def get_data_expense_account(filters, period_list):
	
	data = []
	conditions = get_conditions(filters)
	fy = filters.fiscal_year
	grand_total = {}
	exp_acc_total = {}
	grand_tot = 0
	for d in period_list:
		grand_total[d.key] = 0
	
	for exp_acc in frappe.db.sql(
		"""
			select distinct(expense_account) as expense_account
			from `tabExpense Head`
		""",as_dict=1):

		exp_head = frappe.db.sql("""
			select expense_head as expense_head
			from `tabExpense Head` where expense_account='{}'
		""".format(exp_acc.expense_account), as_dict=1)
		
		row1 = {}
		row_sum = 0
		row1['expense_account'] = exp_acc.expense_account
		data.append(row1)

		for d in period_list:
			exp_acc_total[d.key] = 0
		
		for x in exp_head:
			total = 0
			row = {}
			row['expense_account'] = x.expense_head
		
			for d in period_list:
				query = """
						select sum(epi.amount) as amount
						from `tabEME Invoice` ep
						inner join
						`tabEME Invoice Item` epi
						on epi.parent = ep.name
						where ep.docstatus=1 and epi.expense_head = '{}' and ep.posting_date between '{}' and '{}' {}
					""".format(x.expense_head, d.from_date, d.to_date, conditions)
				amt = frappe.db.sql(query, as_dict=1)
				
				if filters.periodicity == "Yearly":
					row[d.key] = amt[0].amount
				else:
					total += flt(amt[0].amount) 
					row[d.key] = amt[0].amount
					row['total'] = total	
					
				grand_total[d.key] += flt(amt[0].amount)
				exp_acc_total[d.key] += flt(amt[0].amount)

			for d in period_list:
				row1[d.key] = exp_acc_total[d.key]	
			
			row_sum += total
			row1['total'] = row_sum		
			grand_tot += total			
			data.append(row)

	r = {}
	r['expense_account'] = '<b> Grand Total </b>'
	for d in period_list:
		r[d.key] = grand_total[d.key]
		r['total'] = grand_tot
	data.append(r)
	
	return data
		
def get_columns_expense_account(periodicity, period_list, accumulated_values=1):
	columns = [{
		"fieldname": "expense_account",
		"label": _("Expense Account/Head"),
		"fieldtype": "Link",
		"options": "Account",
		"width": 300
	}]

	for period in period_list:
		columns.append({
			"fieldname": period.key,
			"label": period.label,
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		})
	if periodicity != "Yearly":
		if not accumulated_values:
			columns.append({
				"fieldname": "total",
				"label": _("Total"),
				"fieldtype": "Currency",
				"width": 150
			})
	return columns


#===================================================================================================
# The functions below collects data and columns when the purpose is Expense Head and Equipment Type
#===================================================================================================

def get_data_expense_head(filters, period_list):
	data= []
	conditions = get_conditions(filters)
	fy = filters.fiscal_year
	grand_total = {}
	exp_head_total = {}
	grand_tot = 0

	for d in period_list:
		grand_total[d.key] = 0

	for exp_head in frappe.db.sql(
		"""
			select distinct(epi.expense_head) as expense_head
			from `tabEME Invoice` ep
			inner join
			`tabEME Invoice Item` epi
			on epi.parent = ep.name
		""", as_dict=1):
	
		# data.append({'expense_head': '<b>' + exp_head.expense_head + '</b>'})
		row1 = {}
		row_sum = 0
		row1['expense_head'] = '<b>' + exp_head.expense_head + '</b>'
		data.append(row1)

		for d in period_list:
			exp_head_total[d.key] = 0

		for equi_type in frappe.db.sql(
			"""
				select distinct(epi.equipment_type) as equipment_type
				from `tabEME Invoice` ep
				inner join
				`tabEME Invoice Item` epi
				on epi.parent = ep.name
			""", as_dict=1):

			row = {}
			total = 0
			row['expense_head'] = equi_type.equipment_type

			for d in period_list:
				query = """
						select sum(epi.amount) as amount
						from `tabEME Invoice` ep
						inner join
						`tabEME Invoice Item` epi
						on epi.parent = ep.name
						where ep.docstatus=1 and epi.equipment_type = '{}' and epi.expense_head = '{}' and ep.posting_date between '{}' and '{}' {}
					""".format(equi_type.equipment_type, exp_head.expense_head, d.from_date, d.to_date, conditions)
				
				amt = frappe.db.sql(query, as_dict=1)
				
				if filters.periodicity == "Yearly":
					row[d.key] = amt[0].amount
				else:
					total += flt(amt[0].amount) 
					row[d.key] = amt[0].amount
					row['total'] = total
				grand_total[d.key] += flt(amt[0].amount)
				exp_head_total[d.key] += flt(amt[0].amount)

			for d in period_list:
				row1[d.key] = exp_head_total[d.key]
			
			row_sum += total
			row1['total'] = row_sum		
			grand_tot += total

			if filters.periodicity == "Yearly":
				for d in period_list:
					if row[d.key]:
						data.append(row)
			elif total != 0:
					data.append(row)
	r = {}
	r['expense_head'] = '<b> Grand Total </b>'
	for d in period_list:
		r[d.key] = grand_total[d.key]
		r['total'] = grand_tot
	data.append(r)

	return data

def get_columns_expense_head(periodicity, period_list, accumulated_values=1):
	columns = [{
		"fieldname": "expense_head",
		"label": _("Expense Head/Equipment Type"),
		"fieldtype": "Link",
		"options": "Expense Head",
		"width": 300
	}]
	
	for period in period_list:
		columns.append({
			"fieldname": period.key,
			"label": period.label,
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		})
	if periodicity != "Yearly":
		if not accumulated_values:
			columns.append({
				"fieldname": "total",
				"label": _("Total"),
				"fieldtype": "Currency",
				"width": 150
			})
	return columns


def get_conditions(filters):
	conditions = ""
	if filters.get("cost_center"):
		conditions += " and cost_center = '{}'".format(filters.cost_center)
	if filters.get("branch"):
		conditions += " and branch = '{}'".format(filters.branch)
	if filters.get("supplier"):
		conditions += " and supplier = '{}'".format(filters.supplier)
	return conditions
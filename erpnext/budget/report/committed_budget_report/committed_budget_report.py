# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr

def execute(filters=None):
	validate_filters(filters)
	columns = get_columns()
	queries = construct_query(filters)
	data = get_data(queries)

	return columns, data

def get_data(query):
	data = []
	datas = frappe.db.sql(query, as_dict=True)
	for d in datas:
		item_name = None
		if d.item_code:
			item_name= frappe.db.get_value("Item", d.item_code, "item_name")
		row = {
			"account": d.account, 
			"cost_center": d.cost_center,
			"reference_type": d.reference_type,
			"reference_no": d.reference_no,
			"project": d.project,
			"reference_date": d.reference_date,
			"amount": d.amount,
			"item_name": item_name
		}
		data.append(row)
	return data

def construct_query(filters=None):
	condition = ""
	if filters.budget_against == "Project":
		if filters.project:
			condition += " and com.project = '{}'".format(filters.project)
		else:
			condition += " and (com.project != '' or com.project is NOT NULL)"
	else:
		if filters.cost_center:
			condition += " and com.cost_center = '{}' and (com.project = '' or com.project is NULL)".format(filters.cost_center)
		else:
			condition += " and (com.project = '' or com.project is NULL)"
	
	query = """SELECT com.account, com.cost_center, com.reference_type, com.reference_no, 
				com.reference_date, com.project, com.amount, com.item_code
				FROM `tabCommitted Budget` com 
				WHERE com.docstatus = 1 
				and com.reference_date BETWEEN '{0}' AND '{1}'
				and com.closed = 0
				and not exists (select 1 
						from `tabConsumed Budget` cb 
						where cb.account = com.account 
						and cb.cost_center = com.cost_center 
						and cb.com_ref = com.name
						and (IFNULL(com.item_code,1) = 1 OR cb.item_code = com.item_code)
				)
				{2}
				order by com.reference_date desc
				""".format(str(filters.from_date), str(filters.to_date), condition)
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


def get_columns():
	return [
		{
		  "fieldname": "account",
		  "label": "Account Head",
		  "fieldtype": "Link",
		  "options": "Account",
		  "width": 250
		},
		{
		  "fieldname": "cost_center",
		  "label": "Cost Center",
		  "fieldtype": "Link",
		  "options": "Cost Center",
		  "width": 250
		},
		{
		  "fieldname": "amount",
		  "label": "Amount",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "reference_type",
		  "label": "Reference Type",
		  "fieldtype": "Data",
		  "width": 140
		},
		{
		  "fieldname": "reference_no",
		  "label": "Reference No",
		  "fieldtype": "Data",
		  "width": 130
		},
		{
		  "fieldname": "item_name",
		  "label": "Item",
		  "fieldtype": "Data",
		  "width": 120
		},
		{
		  "fieldname": "reference_date",
		  "label": "Commit Date",
		  "fieldtype": "Date",
		  "width": 120
		},
		{
		  "fieldname": "project",
		  "label": "Project",
		  "fieldtype": "Data",
		  "width": 120
		}
	]
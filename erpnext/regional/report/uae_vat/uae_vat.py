# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data

def get_columns():
	return [
		{
			"fieldname": "no",
			"label": "No",
			"fieldtype": "Data",
			"width": 50
		},
		{
			"fieldname": "legend",
			"label": "Legend",
			"fieldtype": "Data",
			"width": 300
		},
		{
			"fieldname": "amount",
			"label": "Amount (AED)",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "vat_amount",
			"label": "VAT Amount (AED)",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "adjustment",
			"label": "Adjustment (AED)",
			"fieldtype": "Currency",
			"width": 100
		}
	]

def get_data(filters = None):
	data = []
	total_emiratewise = get_total_emiratewise(filters)
	emirates = get_emirates()
	amounts_by_emirate = {}
	for d in total_emiratewise:
		emirate, amount, vat= d
		amounts_by_emirate[emirate] = {
				"legend": emirate,
				"amount": amount,
				"vat_amount": vat
			}
	for d, emirate in enumerate(emirates, 97):
		if emirate in amounts_by_emirate:
			amounts_by_emirate[emirate]["no"] = f'1{chr(d)}'
			amounts_by_emirate[emirate]["legend"] = f'Standard rated supplies in {emirate}'
			data.append(amounts_by_emirate[emirate])
		else:
			data.append(
				{
					"no": f'1{chr(d)}',
					"legend": f'Standard rated supplies in {emirate}',
					"amount": 0,
					"vat_amount": 0
				}
			)
	return data


def get_total_emiratewise(filters):
	conditions = get_conditions(filters)
	print(f"""
		select emirate, sum(total), sum(total_taxes_and_charges) from `tabSales Invoice`
		where docstatus = 1 {conditions}
		group by `tabSales Invoice`.emirate;
		""")
	return frappe.db.sql(f"""
		select emirate, sum(total), sum(total_taxes_and_charges) from `tabSales Invoice`
		where docstatus = 1 {conditions}
		group by `tabSales Invoice`.emirate;
		""", filters)

def get_emirates():
	return [
		'Abu Dhabi',
		'Dubai',
		'Sharjah',
		'Ajman',
		'Umm Al Quwain',
		'Ras Al Khaimah',
		'Fujairah'
	]

def get_conditions(filters):
	conditions = ""

	for opts in (("company", " and company=%(company)s"),
		("from_date", " and posting_date>=%(from_date)s"),
		("to_date", " and posting_date<=%(to_date)s")):
			if filters.get(opts[0]):
				conditions += opts[1]
	return conditions
# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	columns = [
		{
			"fieldname": "branch",
			"label" : "Branch",
			"fieldtype" : "Link",
			"options": "Branch",
			"width": 120
		},
		{
			"fieldname": "cost_center",
			"label" : "Cost Center",
			"fieldtype" : "Data",
			"width": 120
		},
		{
			"fieldname": "posting_date",
			"label" : "Posting Date",
			"fieldtype" : "Date",
			"width": 120
		},
		{
			"fieldname": "payment_type",
			"label" : "Payment Type",
			"fieldtype" : "Data",
			"width": 120
		}

	]
	return columns

def get_data(filters):
	cond = get_conditions(filters)
	data = frappe.db.sql(
		"""
		select 
			branch, cost_center, posting_date, payment_type
		from `tabRental Payment`
		where docstatus = 1
		{condition}
		""".format(condition=cond)
	)
	return data

def get_conditions(filters):
	cond = ""
	if filters.branch:
		cond += "and branch='{}'".format(filters.branch)	
	return cond
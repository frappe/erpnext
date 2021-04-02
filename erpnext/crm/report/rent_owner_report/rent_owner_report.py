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
			"fieldname": "dzongkhag",
			"label" : "Dzongkhag",
			"fieldtype" : "Data",			
			"width": 120
		},
		{
			"fieldname": "location",
			"label" : "Location",
			"fieldtype" : "Data",
			"width": 120
		},
		{
			"fieldname": "building_name",
			"label" : "Building Name",
			"fieldtype" : "Data",
			"width": 120
		},
			{
			"fieldname": "owner_account_number",
			"label" : "Owner Account Number",
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
			dzongkhag, location, building_name, owner_account_number
		from `tabRent Owners`
		where docstatus = 1
		{condition}
		""".format(condition=cond)
	)
	return data

def get_conditions(filters):
	cond = ""
	if filters.dzongkhag:
		cond += "and dzongkhag='{}'".format(filters.dzongkhag)	

	if filters.building_name:
		cond += "and building_name='{}'".format(filters.building_name)	
	return cond
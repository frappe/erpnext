# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	if filters.to_date and filters.from_date : validate_date(filters)
	columns, data = get_columns(), get_data(filters)
	return columns, data

def validate_date(filters):
	if filters.to_date < filters.from_date :
		frappe.throw("From Date cannot be grater than To Date")

def get_data(filters):
	conds = ""
	conds = get_conds(filters)
	return frappe.db.sql("""
		SELECT
			ttl.name,ttl.branch,ttl.cost_center,ttl.posting_date,ttl.warehouse,
			tlt.item_name,tlt.equipment,tlt.equipment_type,tlt.equipment_category,
			tlt.distance,tlt.qty,tlt.rate,tlt.amount
		FROM
			`tabTrip Log` as ttl
		INNER JOIN
			`tabTrip Log Item` as tlt
		ON	
			tlt.parent = ttl.name 
		{0}
	""".format(conds))

def get_conds(filters):
	conds = " WHERE ttl.docstatus = 1 "
	if filters.from_date :
		conds += " AND ttl.posting_date >= '{}'".format(filters.from_date)
	if filters.to_date:
		conds += " AND ttl.posting_date <= '{}' ".format(filters.to_date)
	if filters.branch:
		conds += " AND ttl.branch = '{}'".format(filters.branch)
	if filters.warehouse:
		conds += " AND ttl.warehouse = '{}'".format(filters.warehouse)
	return conds
def get_columns():
	return [
		{
			"fieldname":"reference","label": ("Reference"),	"fieldtype": "Link","options":"Trip Log","width": 150
		},
		{
			"fieldname":"branch","label": ("Branch"),"fieldtype": "Link","options":"Branch","width": 200
		},
		{
			"fieldname":"cost_center","label": ("Cost Center"),"fieldtype": "Link",	"options":"Cost Center","width": 200
		},
		{
			"fieldname":"posting_date",	"label": ("Posting Date"),	"fieldtype": "Date","width": 100
		},
		{
			"fieldname":"warehouse", "label": ("Warehouse"), "fieldtype": "Link",	"options":"Warehouse", "width": 300
		},
		{
			"fieldname":"item_name","label": ("Item Name"),	"fieldtype": "Data","width": 150
		},
		{
			"fieldname":"vehicle_no","label": ("Vehicle No"),"fieldtype": "Data","width": 100
		},
		{
			"fieldname":"equipment_type",	"label": ("Equipment type"),"fieldtype": "Data","width": 150
		},
		{
			"fieldname":"equipment_type","label": ("Equipment Category"),"fieldtype": "Data","width": 150
		},
		{
			"fieldname":"distance",	"label": ("Distance"),	"fieldtype": "Float",	"width": 100
		},
		{
			"fieldname":"qty", "label": ("Quantity(MT)"),	"fieldtype": "Float",	"width": 100
		},
		{
			"fieldname":"rate",	"label": ("Rate"),	"fieldtype": "Currency","width": 150
		},
		{
			"fieldname":"amount","label": ("Amount"),	"fieldtype": "Currency","width": 150
		}
	]
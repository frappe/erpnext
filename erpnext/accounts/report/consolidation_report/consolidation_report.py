# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate


def execute(filters=None):
	filter = frappe._dict({
		'from_date':filters.from_date,
		'to_date':filters.to_date,
		'is_inter_company':filters.is_inter_company
	})
	columns, data 				= get_columns(), get_data(filter,'No')
	return columns, data

def get_data(filters,from_rest_api=None):
	cond = ''
	if filters['is_inter_company'] == 'Yes':
		cond += ' and interco != "I_NONE"'
	d = frappe.db.sql('''
					 SELECT name, from_date, to_date
      					FROM `tabConsolidation Transaction`  
           				WHERE from_date = '{}' AND to_date = '{}' ORDER BY name desc limit 1
					  '''.format(filters['from_date'],filters['to_date']),as_dict=True)
	if not d:
		return []
	parent_name = d[0].name
	from_date = d[0].from_date
	to_date = d[0].to_date
	if from_rest_api == 'Yes': 
		return frappe.db.sql('''
				SELECT account_code, account,entity, segment, flow,
    			interco, time,SUM(amount) as amount
				FROM `tabConsolidation Transaction Item` where parent = '{}'
				{} GROUP BY interco, account
				'''.format(parent_name,cond),as_dict=1) 
	elif from_rest_api == 'No':
		return frappe.db.sql('''
				SELECT account_code, account,entity, segment, flow,
				interco, time,'{0}' as from_date, 
    			'{1}' as to_date, SUM(opening_debit), SUM(opening_credit),
       			SUM(debit), SUM(credit), SUM(amount) as amount
				FROM `tabConsolidation Transaction Item` where parent = '{2}' 
				{3} GROUP BY interco, account
				'''.format(getdate(from_date), getdate(to_date), parent_name, cond))

def get_columns():
	return [
		{
			"fieldname":"account_code",
			"label":"Account Code",
			"fieldtype":"Data",
			"width":80
		},
		{
			"fieldname":"account",
			"label":"Account",
			"fieldtype":"Link",
			"options":"DHI GCOA Mapper",
			"width":250
		},
		{
			"fieldname":"entity",
			"label":"Entity",
			"fieldtype":"Data",
			"width":60
		},
		{
			"fieldname":"segment",
			"label":"Segment",
			"fieldtype":"Data",
			"width":60
		},
		{
			"fieldname":"flow",
			"label":"Flow",
			"fieldtype":"Data",
			"width":60
		},
		{
			"fieldname":"interco",
			"label":"Interco",
			"fieldtype":"Data",
			"width":60
		},
		{
			"fieldname":"time",
			"label":"Time",
			"fieldtype":"Data",
			"width":80
		},
		{
			"fieldname":"from_date",
			"label":"From Date",
			"fieldtype":"Date",
			"width":80
		},
		{
			"fieldname":"to_date",
			"label":"To Date",
			"fieldtype":"Date",
			"width":80
		},
		{
			"fieldname":"opening_debit",
			"label":"Opening(Dr)",
			"fieldtype":"Currency",
			"width":130
		},
		{
			"fieldname":"opening_credit",
			"label":"Opening(Cr)",
			"fieldtype":"Currency",
			"width":130
		},
		{
			"fieldname":"debit",
			"label":"Debit",
			"fieldtype":"Currency",
			"width":150
		},
		{
			"fieldname":"credit",
			"label":"Credit",
			"fieldtype":"Currency",
			"width":150
		},
		{
			"fieldname":"amount",
			"label":"Amount",
			"fieldtype":"Currency",
			"width":150
		},
	]


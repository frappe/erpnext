# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from pypika import functions as fn
from frappe import _, qb, throw

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_data(filters):
	cond = get_condidion(filters)
	if filters.show_aggregate:
		return frappe.db.sql("""
			SELECT mineral_raising_group, coal_raising_type, tier,
				sum(no_of_labours) as no_of_labours,
				sum(product_qty) as product_qty,
				sum(machine_hours) as machine_hours,
				sum(amount) as amount,
				sum(machine_payable) as machine_payable,
				sum(grand_amount) as grand_amount,
				sum(penalty_amount) as penalty_amount
			FROM `tabProduction` 
			WHERE docstatus = 1
			AND branch = '{}' 
			AND posting_date between '{}'
			AND '{}'
			{} 
			AND (tier = '' OR tier is not null) 
			AND (coal_raising_type != '' or coal_raising_type is not null)
			AND coal_raising_type IN ('Manual', 'Machine Sharing', 'SMCL Machine')
			group by mineral_raising_group, coal_raising_type
		""".format(filters.branch,filters.from_date,filters.to_date,cond),as_dict=1)
	return frappe.db.sql("""
		SELECT 
			name as reference,posting_date,coal_raising_type, 
			mineral_raising_group,tier, no_of_labours,machine_hours,
			product_qty,amount,machine_payable,
			grand_amount, penalty_amount
		FROM `tabProduction`
		WHERE docstatus = 1
		AND branch = '{}' 
		AND posting_date between '{}'
		AND '{}'
		{}
		AND coal_raising_type IN ('Manual', 'Machine Sharing', 'SMCL Machine')
		""".format(filters.branch,filters.from_date,filters.to_date,cond),as_dict=1)

def get_condidion(filters=None):
	cond = ''
	if filters.from_date > filters.to_date:
		frappe.throw('From Date cannot be after To Date')
	if filters.coal_raising_type:
		cond += " AND coal_raising_type ='{}'".format(filters.coal_raising_type)
	if filters.group:
		cond += " AND mineral_raising_group ='{}' ".format(filters.group)
	if filters.tier:
		cond += " AND tier = '{}' ".format(filters.tire)
	return cond

def get_columns(filters):
	col = []
	if not filters.show_aggregate:
		col += [
		{
			'fieldname':'reference','fieldtype':'Link','options':'Production',	'width':110,'label':'Reference'
		},
		{
			'fieldname':'posting_date','fieldtype':'Date','label':'Posting Date','width':100
		}]

	col += [
		{
			'fieldname':'coal_raising_type','fieldtype':'Data',	'label':'Coal Raising Type','width':120
		},
		{
			'fieldname':'mineral_raising_group','fieldtype':'Link',	'label':'Mineral Raising Group','options':'Mineral Raising Group','width':140
		},
		{
			'fieldname':'tier','fieldtype':'Link','label':'Tier','options':'Tier','width':120
		},
		{
			'fieldname':'no_of_labours','fieldtype':'Float','label':'No. Labours','width':90
		},
		{
			'fieldname':'machine_hours','fieldtype':'Float','width':90,'label':'Machine Hrs'
		},
		{
			'fieldname':'machine_payable',	'fieldtype':'Currency',	'label':'Machine Payable','width':110
		},
		{
			'fieldname':'product_qty',	'fieldtype':'Float','label':'Quantity',	'width':90
		},
		{
			'fieldname':'grand_amount',	'fieldtype':'Currency',	'label':'Grand Amount',	'width':120
		},
		{
			'fieldname':'penalty_amount','fieldtype':'Currency','label':'Penalty Amount','width':120
		},
		{
			'fieldname':'amount','fieldtype':'Currency','label':'Net Amount','width':120
		},
	]
	return col
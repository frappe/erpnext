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
	p = qb.DocType("Production")
	query = (qb.from_(p))
	if filters.from_date > filters.to_date:
		frappe.throw('From Date cannot be after To Date')
	if filters.coal_raising_type:
		query = (query.where( p.coal_raising_type == filters.coal_raising_type))
		cond += " AND coal_raising_type ='{}'".format(filters.coal_raising_type)
	if filters.mineral_raising_group:
		query = (query.where( p.mineral_raising_group == filters.mineral_raising_group))
		cond += " AND `group` ='{}' ".format(filters.group)
	if filters.tier:
		cond += " AND tier = '{}' ".format(filters.tier)
		query = (query.where( p.tier == filters.tier))
	if filters.branch:
		query = (query.where( p.branch == filters.branch))
	if filters.show_aggregate:
		return (query.select(p.mineral_raising_group, p.coal_raising_type, p.tier,
							fn.Sum(p.no_of_labours).as_("no_of_labours"),
							fn.Sum(p.product_qty).as_("product_qty"),
							fn.Sum(p.machine_hours).as_("machine_hours"),
							fn.Sum(p.amount).as_("amount"),
							fn.Sum(p.machine_payable).as_("machine_payable"),
							fn.Sum(p.grand_amount).as_("grand_amount"),
							fn.Sum(p.penalty_amount).as_("penality_amount"))
						.where((p.posting_date >= filters.from_date)
								& (p.posting_date <= filters.to_date) 
								& (p.docstatus == 1) 
								& (p.coal_raising_type).isin('Manual', 'Machine Sharing', 'SMCL Machine'))
						.groupby(p.mineral_raising_group)
						.groupby(p.coal_raising_type)).run(as_dict=1)
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
		cond += " AND `group` ='{}' ".format(filters.group)
	if filters.tire:
		cond += " AND tire = '{}' ".format(filters.tire)
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
			'fieldname':'tire','fieldtype':'Link','label':'Tire','options':'Tire','width':120
		},
		{
			'fieldname':'no_of_labours','fieldtype':'Float','label':'No. Labours','width':90
		},
		{
			'fieldname':'machine_hours','fieldtype':'Float','width':90
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
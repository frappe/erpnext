# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe.utils import flt

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data
	
def get_columns(filters):
	columns = [
		{
			"fieldname": "customer",
			"label": "CUSTOMER",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 200
		},
		{
			"fieldname": "country",
			"label": "Country",
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "territory",
			"label": "TERRITORY",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 100
		},
		{
			"fieldname": "item_code",
			"label": "ITEM CODE",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100
		},
		{
			"fieldname": "item_name",
			"label": "ITEM 	NAME",
			"fieldtype": "data",
			"width": 150
		},
		{
			"fieldname": "item_type",
			"label": "ITEM  TYPE",
			"fieldtype": "Link",
			"options": "Item Type",
			"width": 150
		},

		{
			"fieldname": "opening",
			"label": "OPENING",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		},
		{
			"fieldname": "qty",
			"label": "QUANTITY SOLD",
			"fieldtype": "Float",
			"fieldtype": "data",
			"width": 120
		},
		{
			"fieldname": "billed_amount",
			"label": "BILLED AMOUNT",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		},
		{
			"fieldname": "received_amount",
			"label": "PAYMENT RECEIVED",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		},
		{
			"fieldname": "closing",
			"label": "CLOSING BALANCE",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		}
	]
	return columns
def get_data(filters):
	data = []
	row = []
	query = """ select si.name, si.customer, sii.item_code, sii.item_name, sii.item_type, sum(case when si.posting_date < '{from_date}' then ifnull(si.outstanding_amount, 0) else 0 end) as opening, sum(case when si.posting_date between '{from_date}' and '{to_date}' then ifnull(sii.accepted_qty, 0) else 0 end) as accepted_qty, sum(case when si.posting_date between '{from_date}' and '{to_date}' then ifnull(sii.amount + sii.excess_amt + si.total_charges + sii.normal_loss_amt + sii.abnormal_loss_amt, 0) else 0 end) as billed_amount from `tabSales Invoice` si, `tabSales Invoice Item` sii where sii.parent = si.name and si.docstatus = 1""".format(from_date = filters.from_date, to_date = filters.to_date)
	if filters.item_code:
		query += " and sii.item_code = '{0}'".format(filters.item_code)

	if filters.cost_center:
		query += " and si.cost_center = '{0}'".format(filters.cost_center)

	if filters.country:
		query += " and exists ( select 1 from `tabCustomer` where country = '{0}') ".format(filters.country)

	if filters.item_type:
		query += " and sii.item_type = '{0}'".format(filters.item_type)

	query += " group by si.customer, sii.item_code"
	dat = frappe.db.sql(query, as_dict = 1)
	for d in dat:
		territory, country = get_customer_details(filters, d.customer)
		received_amount = payment_details(filters, d.name)
		closing_amt =  flt(d.opening) + flt(d.billed_amount) - flt(received_amount)	
		if flt(d.opening) + flt(d.accepted_qty) + flt(d.billed_amount) + flt(received_amount) + flt(closing_amt) > 0:
			row = [d.customer, country, territory, d.item_code, d.item_name, d.item_type, d.opening, d.accepted_qty, d.billed_amount, received_amount, closing_amt]
			data.append(row)
	return data

def get_customer_details(filters, customer):
	cust = frappe.db.sql(""" select territory, country from `tabCustomer` where name = "{0}" """.format(customer), as_dict = 1)
	if cust:
		return cust[0].territory, cust[0].country
	else:
		 return ''

def payment_details(filters, sales_invoice = None):
	payment = frappe.db.sql(""" select sum(ifnull(per.allocated_amount, 0)) as payment_received from `tabPayment Entry Reference` per, `tabPayment Entry` pe  where per.parent = pe.name and pe.posting_date between '{0}' and '{1}' and per.reference_name = "{2}" and pe.docstatus = 1 """.format(filters.from_date, filters.to_date, sales_invoice), as_dict = 1)
	if payment:
		return payment[0].payment_received
	else:
		return 0.0
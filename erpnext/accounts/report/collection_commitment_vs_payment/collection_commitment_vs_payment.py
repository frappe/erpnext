# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	columns = get_columns(filters)
	conditions = get_conditions(filters)
	data = get_data(conditions, filters)
	return columns, data

def get_conditions(filters):
	conditions = ""
	if filters.get("customer"):
		conditions += " AND prc.customer = '{0}'".format(filters.get("customer"))
		
	return conditions	

def get_columns(filters):
	print(" Columns are here ")	
	column_lst =[
		{
			"fieldname": "customer",
			"label": "Customer",
			"width": 120,
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "customer_name",
			"label": "Customer Name",
			"width": 200,
			"fieldtype": "Data"
		},
		{
			"fieldname": "c_amount",
			"label": "Committed Amount",
			"width": 100,
			"fieldtype": "Currency"
		},
		{
			"fieldname": "col_amount",
			"label": "Collected Amount",
			"width": 100,
			"fieldtype": "Currency"
		},
		{
			"fieldname": "company",
			"label": "Company",
			"width": 200,
			"fieldtype": "Link",
			"options": "Company"
		}]
	
	return column_lst
def get_data(conditions, filters):	
	from_date = filters.get("from_date") 
	to_date = filters.get("to_date")
	print(" In get Data", conditions)
	query = frappe.db.sql("""
							Select prc.customer , prc.customer_name, sum(prc.commitment_amount) as c_amount, 
							CASE when 1
								THEN (Select sum(pe.paid_amount) from `tabPayment Entry` pe 
									where pe.party = prc.customer and pe.payment_type ="Receive" 
									and pe.posting_date between '{0}' and '{1}')
								Else 0
							End as col_amount, prc.company
							from `tabPayment Receivable Commitment` prc 
							where prc.company = '{3}' and prc.commitment_status ="Active" 
							and prc.commitment_date between '{0}' and '{1}' {2}
							
							group by prc.customer
						""".format(from_date, to_date, conditions, filters.get("company")))

	return query					



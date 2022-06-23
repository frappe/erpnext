# Copyright (c) 2022, Dexciss Technologies Pvt. Ltd. and contributors
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
	# print(" Columns are here ")	
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
			"fieldname": "c_date",
			"label": "Commitment Date",
			"width": 100,
			"fieldtype": "Date"
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
		]
	
	return column_lst
def get_data(conditions, filters):	
	from_date = filters.get("from_date") 
	to_date = filters.get("to_date")
	# print(" In get Data", conditions)
	query = frappe.db.sql("""
							Select prc.customer as customer, prc.customer_name as customer_name, prc.commitment_date as c_date, sum(prc.commitment_amount) as c_amount, 
							IF ( (Select sum(pe.paid_amount) from `tabPayment Entry` pe 
									where pe.party = prc.customer and pe.payment_type ="Receive" 
									and pe.posting_date <= '{0}' ) < sum(prc.commitment_amount),
								
								(Select sum(pe.paid_amount) from `tabPayment Entry` pe 
									where pe.party = prc.customer and pe.payment_type ="Receive" 
									and pe.posting_date <= '{0}'), 0) as col_amount, prc.company
							from `tabPayment Receivable Commitment` prc 
							where prc.company = '{2}' and prc.commitment_status ="Active" 
							
							and prc.commitment_date <= '{0}'  {1}
							
							group by prc.customer
						""".format(to_date, conditions, filters.get("company")), as_dict= 1)

	data = []
	for q in query:
		if q.get("col_amount") > 0:
			data.append(q)
			# print(" q ",q)
	return data	




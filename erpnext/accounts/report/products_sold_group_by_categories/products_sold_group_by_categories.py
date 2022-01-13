# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	if not filters: filters = {}
	data = []
	columns = [
		{
   			"fieldname": "category",
  			"fieldtype": "Data",
  			"label": "Category",
  		},
		{
   			"fieldname": "product",
  			"fieldtype": "Data",
  			"label": "Product",
  		},
		{
			"fieldname": "total_product",
   			"fieldtype": "Currency",
   			"label": "Total Product"
		},
		{
   			"fieldname": "product_description",
  			"fieldtype": "Data",
  			"label": "Description",
  		},
		{
			"fieldname": "quantity",
   			"fieldtype": "Float",
   			"label": "Quantity"
		},
		{
			"fieldname": "total_price",
   			"fieldtype": "Currency",
   			"label": "TOTAL"
		}
	]
	data = []

	products = []
	item_groups = []

	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = get_conditions(filters, from_date, to_date)

	sales_invoices = frappe.get_all("Sales Invoice", ["*"], filters = conditions)

	for sale_invoice in sales_invoices:
		products_list = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": sale_invoice.name})

		for product in products_list:
			products.append(product)
	
	for product in products:
		if product.item_group in item_groups:
			exist = True
		else:
			item_groups.append(product.item_group)

	for item_group in item_groups:
		items = []

		group_arr = [{'indent': 0.0, "category": item_group}]
		data.extend(group_arr or [])

		for product in products:
			if item_group == product.item_group:
				product_arr = [{'indent': 1.0, "category":"", "product": product.item_name, "total_product": product.rate, "product_description": product.description, "quantity": product.qty, "total_price": product.amount}]
				items.append(product_arr)
		
		data.extend(items or [])

	return columns, data

def get_conditions(filters, from_date, to_date):
	conditions = ''

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "posting_time": [">=", "{}"]'.format(filters.get("from_time"))
	conditions += ', "posting_time": ["<=", "{}"]'.format(filters.get("to_time"))
	conditions += ', "naming_series": "{}"'.format(filters.get("prefix"))
	if filters.get("user"):
		conditions += ', "cashier": "{}"'.format(filters.get("user"))
	conditions += '}'

	return conditions

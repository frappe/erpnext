# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	if not filters: filters = {}
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
		total_group = 0
		for item in products:
			if item_group == item.item_group:
				total_group += item.amount

		group_arr = [{'indent': 0.0, "category": item_group, "total_price": total_group}]
		data.extend(group_arr or [])

		items_list = []

		for product in products:
			exist = True
			item_name = product.item_name
			rate = product.rate
			description = product.description
			qty = 0
			amount = 0

			if item_name in items_list:
				exist = True
			else:
				exist = False

			if item_group == product.item_group and exist == False:
				for item in products:
					if item.item_name == product.item_name:
						qty += product.qty
						amount += product.amount

				items_list.append(item_name)
				product_arr = {'indent': 1.0, "category":"", "product": item_name, "total_product": rate, "product_description": description, "quantity": qty, "total_price": amount}
				items.append(product_arr)
		
		data.extend(items or [])

	return columns, data

def get_conditions(filters, from_date, to_date):
	conditions = ''

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("user"):
		conditions += ', "cashier": "{}"'.format(filters.get("user"))
	conditions += '}'

	return conditions

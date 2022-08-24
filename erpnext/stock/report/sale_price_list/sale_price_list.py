# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns, columns_list = return_columns(filters)
	data = return_data(filters, columns_list)
	return columns, data

def return_data(filters, lists):
	data = []	

	if filters.get("item_code"):
		item = frappe.get_all("Item Price", ["*"], filters = {"item_code": filters.get("item_code")})
		name = item[0].item_code + ":" + item[0].item_name
		row = [name]

		for list in lists:
			condition_items = conditions_item(filters, list)
			items = frappe.get_all("Item Price", ["*"], filters = condition_items)
			
			if len(items) > 0:
				row.append(items[0].price_list_rate)
			else:
				row.append(0)
		
		data.append(row)
	else:
		filters_item = filters_items(filters)
		items = frappe.get_all("Item", ["*"], filters = filters_item)

		for item in items:
			name = item.item_code + ":" + item.item_name
			row = [name]

			for list in lists:
				condition_items = conditions_items(filters, item.item_code, list)
				items = frappe.get_all("Item Price", ["*"], filters = condition_items)
				
				if len(items) > 0:
					row.append(items[0].price_list_rate)
				else:
					row.append(0)
			
			data.append(row)

	return data

def return_columns(filters):
	condition = conditions_columns(filters)
	lists = frappe.get_all("Price List", ["*"], filters = condition)

	columns_list = []

	columns = [_("Item Name") + "::240"]

	for list in lists:
		columns += [_(list.name) + ":Currency:120"]
		columns_list.append(list.name)

	return columns, columns_list

def conditions_columns(filters):
	conditions = ''	

	conditions += "{"
	conditions += '"selling": 1'
	conditions += '}'

	return conditions

def conditions_item(filters, list):
	conditions = ''	

	conditions += "{"
	conditions += '"price_list": "{}"'.format(list)	
	conditions += ', "item_code": "{}"'.format(filters.get("item_code"))
	conditions += '}'

	return conditions

def conditions_items(filters, item_code, list):
	conditions = ''	

	conditions += "{"
	conditions += '"price_list": "{}"'.format(list)	
	conditions += ', "item_code": "{}"'.format(item_code)
	conditions += '}'

	return conditions

def filters_items(filters):
	conditions = ''	

	conditions += "{"
	conditions += '"company": "{}"'.format(filters.get("company"))
	if filters.get("item_group"): conditions += ', "item_group": "{}"'.format(filters.get("item_group"))
	if filters.get("category_for_sale"): conditions += ', "category_for_sale": "{}"'.format(filters.get("category_for_sale"))
	conditions += '}'

	return conditions
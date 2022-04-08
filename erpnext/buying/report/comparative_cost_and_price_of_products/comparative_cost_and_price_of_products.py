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
		row = [item[0].item_code, item[0].item_name]

		condition_items_buying = frappe.get_all("Purchase Invoice Item", "*", filters = {"item_code": item[0].item_code})

		if len(condition_items_buying) > 0:
			for i in range(3):
				if len(condition_items_buying) >= i + 1:
					row.append(condition_items_buying[i].rate)
				else:
					row.append(0)
		else:
			for i in range(3):
				row.append(0)

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
			row = [item.item_code, item.item_name]

			condition_items_buying = frappe.get_all("Purchase Invoice Item", "*", filters = {"item_code": item.item_code})

			if len(condition_items_buying) > 0:
				for i in range(3):
					if len(condition_items_buying) >= i + 1:
						row.append(condition_items_buying[i].rate)
					else:
						row.append(0)
			else:
				for i in range(3):
					row.append(0)

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

	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"width": 120
		},
		{
			"label": _("Cost 1"),
			"fieldname": "cost_1",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Cost 2"),
			"fieldname": "cost_2",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Cost 3"),
			"fieldname": "cost_3",
			"fieldtype": "Currency",
			"width": 120
		},
	]

	for list in lists:
		columns += [
			{
			"label": _(list.name),
			"fieldname": "{}".format(list.name),
			"fieldtype": "Currency",
			"width": 120
			},
		]
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
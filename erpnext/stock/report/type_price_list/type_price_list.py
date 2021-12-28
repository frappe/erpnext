# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Item Name") + "::240",_("Price List") + "::240", _("Rate") + ":Currency:120"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	condition = conditions(filters)
	lists = frappe.get_all("Price List", ["*"], filters = condition)

	for list in lists:
		condition_items = conditions_items(filters, list.name)
		items = frappe.get_all("Item Price", ["*"], filters = condition_items)

		for item in items:
			row = [item.item_name, item.price_list, item.price_list_rate]
			data.append(row)
	
	return data

def conditions(filters):
	conditions = ''	

	conditions += "{"
	if filters.get("type") == "Buying":
		conditions += '"buying": 1'

	if filters.get("type") == "Selling":
		conditions += '"selling": 1'
	conditions += '}'

	return conditions

def conditions_items(filters, list):
	conditions = ''	

	conditions += "{"
	conditions += '"price_list": "{}"'.format(list)
	if filters.get("item_code"):
		conditions += ', "item_code": "{}"'.format(filters.get("item_code"))
	if filters.get("item_group"):
		conditions += ', "item_group": "{}"'.format(filters.get("item_group"))
	conditions += '}'

	return conditions
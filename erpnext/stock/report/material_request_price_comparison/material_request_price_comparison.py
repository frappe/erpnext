# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns, data = insertData(filters)	
	return columns, data

def insertData(filters):
	column = [_(filters.get("Category_purchase")) + "::140"]
	column.append(_("Quantity") + ":Int:120")
	dat = []
	redata = []
	conditions = get_conditions(filters)
	material_request_list = frappe.get_all("Material Request", ["name"], filters = conditions)

	for mq in material_request_list:
		material_request_Item_list = frappe.get_all("Material Request Item", ["item_code, item_name, qty"], filters = {"parent":mq.name})

		price_lists = frappe.get_all("Price List", ["name", "price_list_name"], filters = {"enabled": 1, "buying": 1})

		if len(column) == 2:
			for plc in price_lists:
				component = str(plc.price_list_name)
				column.append(_(component) + ":Currency:120")			

		for mril in material_request_Item_list:
			Item = frappe.get_all("Item", ["item_code"], filters = {"item_code": mril.item_code, "category_for_purchase": filters.get("Category_purchase")})
			
			if len(Item) > 0:
				row = [mril.item_name]
				row += [mril.qty]
				for pl in price_lists:
					Items_Price = frappe.get_all("Item Price", ["item_code, price_list_rate"], filters = {"price_list":pl.price_list_name, "item_code": mril.item_code})

					if len(Items_Price) > 0:
						row += [Items_Price[0].price_list_rate]
					else:
						row += [0.00]				
				dat.append(row)
		
	for da in dat:
		if len(redata) == 0:
			redata.append(da)
		else:
			check = 0
			for r in redata:				
				if da[0] == r[0]:
					check = 1
					r[1] += da[1]
				
			if check == 0:
				redata.append(da)
	
	return column, redata

def get_conditions(filters):
	conditions = ''

	conditions += "{"
	if filters.get("from_date"): conditions += '"schedule_date": [">=", "{}"], '.format(filters.get("from_date"))
	if filters.get("to_date"): conditions += '"schedule_date": ["<=", "{}"]'.format(filters.get("to_date"))
	conditions += "}"

	return conditions
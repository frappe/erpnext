# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns=get_columns()
	data=get_data(filters,columns)
	return columns, data

def get_columns():
	return [
		_("Item Name") + ":Link/Item:150",
		_("Warehouse") + ":Link/Warehouse:130",
		_("Stock Available") + ":Float:120",
		_("Buying Price List") + ":Data:130",
		_("Buying Rate") + ":Currency:110",
		_("Selling Price List") + ":Data:130",
		_("Selling Rate") + ":Currency:110"
	]

def get_data(filters, columns):
	item_price_qty_data = []
	item_price_qty_data = get_item_price_qty_data(filters)
	return item_price_qty_data

def get_item_price_qty_data(filters):
	item_dicts = []
	conditions = ""
	if filters.get("item_code"):
		conditions += "where a.item_code=%(item_code)s"

	item_results = frappe.db.sql("""select a.item_code as name,a.name as price_list_name,
		b.warehouse as warehouse,b.actual_qty as actual_qty
		from `tabItem Price` a left join `tabBin` b
		ON a.item_code = b.item_code
		{conditions}"""
		.format(conditions=conditions),filters,as_dict=1)

	price_list_names = ",".join(['"' + item['price_list_name'] + '"' for item in item_results])

	buying_price_map = get_buying_price_map(price_list_names)
	selling_price_map = get_selling_price_map(price_list_names)

	item_dicts = [{"Item Name": d['name'],"Item Price List": d['price_list_name'],"Warehouse": d['warehouse'],
				"Stock Available": d['actual_qty']} for d in item_results]
	for item_dict in item_dicts:
		price_list = item_dict["Item Price List"]
		item_dict["Warehouse"] = item_dict["Warehouse"] or ""
		item_dict["Stock Available"] = item_dict["Stock Available"] or 0
		if buying_price_map.get(price_list):
			item_dict["Buying Price List"] = buying_price_map.get(price_list)["Buying Price List"] or ""
			item_dict["Buying Rate"] = buying_price_map.get(price_list)["Buying Rate"] or 0
		if selling_price_map.get(price_list):
			item_dict["Selling Price List"] = selling_price_map.get(price_list)["Selling Price List"] or ""
			item_dict["Selling Rate"] = selling_price_map.get(price_list)["Selling Rate"] or 0
	return item_dicts

def get_buying_price_map(price_list_names):
	buying_price = frappe.db.sql("""
		select
			name,price_list,price_list_rate
		from
			`tabItem Price`
		where
			name in ({price_list_names}) and buying=1
		""".format(price_list_names=price_list_names),as_dict=1)
	buying_price_map = {}
	for d in buying_price:
		name = d["name"]
		buying_price_map[name] = {
			"Buying Price List" :d["price_list"],
			"Buying Rate" :d["price_list_rate"]
		}
	return buying_price_map

def get_selling_price_map(price_list_names):
	selling_price = frappe.db.sql("""
		select
			name,price_list,price_list_rate
		from
			`tabItem Price`
		where
			name in ({price_list_names}) and selling=1
		""".format(price_list_names=price_list_names),as_dict=1)
	selling_price_map = {}
	for d in selling_price:
		name = d["name"]
		selling_price_map[name] = {
			"Selling Price List" :d["price_list"],
			"Selling Rate" :d["price_list_rate"]
		}
	return selling_price_map
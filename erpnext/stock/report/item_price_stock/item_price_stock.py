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
		_("Item Name") + ":Link/Item:160",
		_("Warehouse") + ":Link/Warehouse:100",
		_("Stock Available") + ":Float:130",
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
		conditions += "and a.item_code=%(item_code)s"

	item_results = frappe.db.sql("""select a.name as name,b.name as price_list_name
		from `tabItem` a,`tabItem Price` b
		where a.item_code = b.item_code
		and a.is_stock_item = 1 {conditions}""".format(conditions=conditions),filters,as_dict=1)

	items = ",".join(['"' + item['name'] + '"' for item in item_results])
	price_list_names = ",".join(['"' + item['price_list_name'] + '"' for item in item_results])

	stock_qty_on_hand_map = get_stock_qty_on_hand_map(items)
	buying_price_map = get_buying_price_map(price_list_names)
	selling_price_map = get_selling_price_map(price_list_names)

	item_dicts = [{"Item Name": d['name'],"Item Price List": d['price_list_name']} for d in item_results]
	for item_dict in item_dicts:
		name = item_dict["Item Name"]
		price_list = item_dict["Item Price List"]
		if stock_qty_on_hand_map.get(name):
			item_dict["Warehouse"] = stock_qty_on_hand_map.get(name)["Warehouse"] or ""
			item_dict["Stock Available"] = stock_qty_on_hand_map.get(name)["Stock Available"] or ""
		if buying_price_map.get(price_list):
			item_dict["Buying Price List"] = buying_price_map.get(price_list)["Buying Price List"] or ""
			item_dict["Buying Rate"] = buying_price_map.get(price_list)["Buying Rate"] or 0
		if selling_price_map.get(price_list):
			item_dict["Selling Price List"] = selling_price_map.get(price_list)["Selling Price List"] or ""
			item_dict["Selling Rate"] = selling_price_map.get(price_list)["Selling Rate"] or 0
	return item_dicts

def get_stock_qty_on_hand_map(items):
	stock_details = frappe.db.sql("""
		select
			item_code as item_code,
			warehouse as warehouse,
			sum(actual_qty) as actual_qty
		from
			`tabBin`
		where
			item_code in ({items})
		group by item_code, warehouse
	""".format(items=items),as_dict=1)

	stock_qty_on_hand_map = {}
	for d in stock_details:
		name = d["item_code"]
		stock_qty_on_hand_map[name] = {
			"Item Name" :d["item_code"],
			"Warehouse" :d["warehouse"],
			"Stock Available" :d["actual_qty"]
		}
	return stock_qty_on_hand_map

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
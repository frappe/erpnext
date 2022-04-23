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
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Brand"),
			"fieldname": "brand",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 120
		},
		{
			"label": _("Stock Available"),
			"fieldname": "stock_available",
			"fieldtype": "Float",
			"width": 120
		},
		{
			"label": _("Buying Price List"),
			"fieldname": "buying_price_list",
			"fieldtype": "Link",
			"options": "Price List",
			"width": 120
		},
		{
			"label": _("Buying Rate"),
			"fieldname": "buying_rate",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Selling Price List"),
			"fieldname": "selling_price_list",
			"fieldtype": "Link",
			"options": "Price List",
			"width": 120
		},
		{
			"label": _("Selling Rate"),
			"fieldname": "selling_rate",
			"fieldtype": "Currency",
			"width": 120
		}
	]

def get_data(filters, columns):
	item_price_qty_data = []
	item_price_qty_data = get_item_price_qty_data(filters)
	return item_price_qty_data

def get_item_price_qty_data(filters):
	conditions = ""
	if filters.get("item_code"):
		conditions += "where a.item_code=%(item_code)s"

	item_results = frappe.db.sql("""select a.item_code, a.item_name, a.name as price_list_name,
		a.brand as brand, b.warehouse as warehouse, b.actual_qty as actual_qty
		from `tabItem Price` a left join `tabBin` b
		ON a.item_code = b.item_code
		{conditions}"""
		.format(conditions=conditions), filters, as_dict=1)

	price_list_names = list(set(item.price_list_name for item in item_results))

	buying_price_map = get_price_map(price_list_names, buying=1)
	selling_price_map = get_price_map(price_list_names, selling=1)

	result = []
	if item_results:
		for item_dict in item_results:
			data = {
				'item_code': item_dict.item_code,
				'item_name': item_dict.item_name,
				'brand': item_dict.brand,
				'warehouse': item_dict.warehouse,
				'stock_available': item_dict.actual_qty or 0,
				'buying_price_list': "",
				'buying_rate': 0.0,
				'selling_price_list': "",
				'selling_rate': 0.0
			}

			price_list = item_dict["price_list_name"]
			if buying_price_map.get(price_list):
				data["buying_price_list"] = buying_price_map.get(price_list)["Buying Price List"] or ""
				data["buying_rate"] = buying_price_map.get(price_list)["Buying Rate"] or 0
			if selling_price_map.get(price_list):
				data["selling_price_list"] = selling_price_map.get(price_list)["Selling Price List"] or ""
				data["selling_rate"] = selling_price_map.get(price_list)["Selling Rate"] or 0

			result.append(data)

	return result

def get_price_map(price_list_names, buying=0, selling=0):
	price_map = {}

	if not price_list_names:
		return price_map

	rate_key = "Buying Rate" if buying else "Selling Rate"
	price_list_key = "Buying Price List" if buying else "Selling Price List"

	filters = {"name": ("in", price_list_names)}
	if buying:
		filters["buying"] = 1
	else:
		filters["selling"] = 1

	pricing_details = frappe.get_all("Item Price",
		fields = ["name", "price_list", "price_list_rate"], filters=filters)

	for d in pricing_details:
		name = d["name"]
		price_map[name] = {
			price_list_key :d["price_list"],
			rate_key :d["price_list_rate"]
		}

	return price_map

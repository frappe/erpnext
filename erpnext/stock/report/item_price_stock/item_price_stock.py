# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.stock.doctype.company_restriction.company_restriction import (
	get_allowed_masters_condition,
	get_allowed_warehouses_condition,
)


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters, columns)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 120},
		{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Data", "width": 100},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 120,
		},
		{
			"label": _("Stock Available"),
			"fieldname": "stock_available",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Buying Price List"),
			"fieldname": "buying_price_list",
			"fieldtype": "Link",
			"options": "Price List",
			"width": 120,
		},
		{
			"label": _("Buying Rate"),
			"fieldname": "buying_rate",
			"fieldtype": "Currency",
			"options": "buying_currency",
			"width": 120,
		},
		{
			"label": _("Buying Currency"),
			"fieldname": "buying_currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 50,
			"hidden": 1,
		},
		{
			"label": _("Selling Price List"),
			"fieldname": "selling_price_list",
			"fieldtype": "Link",
			"options": "Price List",
			"width": 120,
		},
		{
			"label": _("Selling Rate"),
			"fieldname": "selling_rate",
			"fieldtype": "Currency",
			"options": "selling_currency",
			"width": 120,
		},
		{
			"label": _("Selling Currency"),
			"fieldname": "selling_currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 50,
			"hidden": 1,
		},
	]


def get_data(filters, columns):
	item_price_qty_data = []
	item_price_qty_data = get_item_price_qty_data(filters)
	return item_price_qty_data


def get_item_price_qty_data(filters):
	item_price = frappe.qb.DocType("Item Price")
	bin = frappe.qb.DocType("Bin")

	bin_join = item_price.item_code == bin.item_code
	if condition := get_allowed_warehouses_condition(bin.warehouse):
		bin_join &= condition

	query = (
		frappe.qb.from_(item_price)
		.left_join(bin)
		.on(bin_join)
		.select(
			item_price.item_code,
			item_price.item_name,
			item_price.name.as_("price_list_name"),
			item_price.brand.as_("brand"),
			bin.warehouse.as_("warehouse"),
			bin.actual_qty.as_("actual_qty"),
		)
	)

	if filters.get("item_code"):
		query = query.where(item_price.item_code == filters.get("item_code"))

	if condition := get_allowed_masters_condition(item_price.item_code, "Item"):
		query = query.where(condition)

	item_results = query.run(as_dict=True)

	price_list_names = list(set(item.price_list_name for item in item_results))

	buying_price_map = get_price_map(price_list_names, buying=1)
	selling_price_map = get_price_map(price_list_names, selling=1)

	result = []
	if item_results:
		for item_dict in item_results:
			data = {
				"item_code": item_dict.item_code,
				"item_name": item_dict.item_name,
				"brand": item_dict.brand,
				"warehouse": item_dict.warehouse,
				"stock_available": item_dict.actual_qty or 0,
				"buying_price_list": "",
				"buying_rate": 0.0,
				"buying_currency": "",
				"selling_price_list": "",
				"selling_rate": 0.0,
				"selling_currency": "",
			}

			price_list = item_dict["price_list_name"]
			if buying_price_map.get(price_list):
				data["buying_price_list"] = buying_price_map.get(price_list)["Buying Price List"] or ""
				data["buying_rate"] = buying_price_map.get(price_list)["Buying Rate"] or 0
				data["buying_currency"] = buying_price_map.get(price_list)["Buying Currency"] or ""
			if selling_price_map.get(price_list):
				data["selling_price_list"] = selling_price_map.get(price_list)["Selling Price List"] or ""
				data["selling_rate"] = selling_price_map.get(price_list)["Selling Rate"] or 0
				data["selling_currency"] = selling_price_map.get(price_list)["Selling Currency"] or ""

			result.append(data)

	return result


def get_price_map(price_list_names, buying=0, selling=0):
	price_map = {}

	if not price_list_names:
		return price_map

	rate_key = "Buying Rate" if buying else "Selling Rate"
	price_list_key = "Buying Price List" if buying else "Selling Price List"
	currency_key = "Buying Currency" if buying else "Selling Currency"

	filters = {"name": ("in", price_list_names)}
	if buying:
		filters["buying"] = 1
	else:
		filters["selling"] = 1

	pricing_details = frappe.get_all(
		"Item Price", fields=["name", "price_list", "price_list_rate", "currency"], filters=filters
	)

	for d in pricing_details:
		name = d["name"]
		price_map[name] = {
			price_list_key: d["price_list"],
			rate_key: d["price_list_rate"],
			currency_key: d["currency"],
		}

	return price_map

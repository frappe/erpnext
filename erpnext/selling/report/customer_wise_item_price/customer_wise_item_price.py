# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _

from erpnext import get_default_company
from erpnext.accounts.party import get_party_details
from erpnext.stock.get_item_details import get_price_list_rate_for


def execute(filters=None):
	if not filters:
		filters = {}

	if not filters.get("customer"):
		frappe.throw(_("Please select a Customer"))

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data


def get_columns(filters=None):
	return [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Selling Rate"), "fieldname": "selling_rate", "fieldtype": "Currency"},
		{
			"label": _("Available Stock"),
			"fieldname": "available_stock",
			"fieldtype": "Float",
			"width": 150,
		},
		{
			"label": _("Price List"),
			"fieldname": "price_list",
			"fieldtype": "Link",
			"options": "Price List",
			"width": 120,
		},
	]


def get_data(filters=None):
	data = []
	customer_details = get_customer_details(filters)

	items = get_selling_items(filters)
	item_stock_map = frappe.get_all(
		"Bin", fields=["item_code", "sum(actual_qty) AS available"], group_by="item_code"
	)
	item_stock_map = {item.item_code: item.available for item in item_stock_map}

	for item in items:
		price_list_rate = get_price_list_rate_for(customer_details, item.item_code) or 0.0
		available_stock = item_stock_map.get(item.item_code)

		data.append(
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"selling_rate": price_list_rate,
				"price_list": customer_details.get("price_list"),
				"available_stock": available_stock,
			}
		)

	return data


def get_customer_details(filters):
	customer_details = get_party_details(party=filters.get("customer"), party_type="Customer")
	customer_details.update(
		{"company": get_default_company(), "price_list": customer_details.get("selling_price_list")}
	)

	return customer_details


def get_selling_items(filters):
	if filters.get("item"):
		item_filters = {"item_code": filters.get("item"), "is_sales_item": 1, "disabled": 0}
	else:
		item_filters = {"is_sales_item": 1, "disabled": 0}

	items = frappe.get_all(
		"Item", filters=item_filters, fields=["item_code", "item_name"], order_by="item_name"
	)

	return items

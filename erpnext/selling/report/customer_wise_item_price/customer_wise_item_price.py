# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, nowdate

from erpnext import get_default_company
from erpnext.accounts.party import _get_party_details
from erpnext.stock.get_item_details import get_item_price


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
	customer_details = get_customer_details(filters)
	items = get_selling_items(filters)
	item_stock_map = get_item_stock_map()

	# the price lists a selling transaction would consult, in order of preference
	price_lists = [customer_details.price_list]
	if frappe.get_single_value("Selling Settings", "fallback_to_default_price_list"):
		price_lists.append(frappe.get_single_value("Selling Settings", "selling_price_list"))
	price_lists = list(dict.fromkeys(pl for pl in price_lists if pl))

	data = []
	for item in items:
		rate, price_list = get_item_selling_rate(item, customer_details.customer, price_lists)
		data.append(
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"selling_rate": rate,
				"price_list": price_list,
				"available_stock": item_stock_map.get(item.item_code),
			}
		)

	return data


def get_item_selling_rate(item, customer, price_lists):
	"""Resolve the rate the given customer would get, scoped and filtered as a transaction is."""
	ctx = frappe._dict({"customer": customer, "uom": item.stock_uom, "transaction_date": nowdate()})
	for price_list in price_lists:
		ctx.price_list = price_list
		# prefer the customer's own price, else fall back to the party-neutral one
		prices = get_item_price(ctx, item.item_code) or get_item_price(
			frappe._dict(ctx, customer=None, supplier=None), item.item_code
		)
		# get_item_price returns (name, price_list_rate, uom) tuples; a zero rate tries the next list
		if prices and (rate := flt(prices[0][1])):
			return rate, price_list

	return 0.0, price_lists[0] if price_lists else None


def get_item_stock_map():
	item_stock = frappe.get_all(
		"Bin", fields=["item_code", "sum(actual_qty) AS available"], group_by="item_code"
	)
	return {item.item_code: item.available for item in item_stock}


def get_customer_details(filters):
	customer_details = _get_party_details(party=filters.get("customer"), party_type="Customer")
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
		"Item", filters=item_filters, fields=["item_code", "item_name", "stock_uom"], order_by="item_name"
	)

	return items

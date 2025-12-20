# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, qb
from frappe.query_builder import Criterion

from erpnext import get_default_company
from erpnext.accounts.party import get_party_details


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


def fetch_item_prices(
	customer: str | None = None,
	price_list: str | None = None,
	selling_price_list: str | None = None,
	items: list | None = None,
):
	price_list_map = frappe._dict()
	ip = qb.DocType("Item Price")
	and_conditions = []
	or_conditions = []
	if items:
		and_conditions.append(ip.item_code.isin([x.item_code for x in items]))
		and_conditions.append(ip.selling.eq(True))

		or_conditions.append(ip.customer.isnull())
		or_conditions.append(ip.price_list.isnull())

		if customer:
			or_conditions.append(ip.customer == customer)

		if price_list:
			or_conditions.append(ip.price_list == price_list)

		if selling_price_list:
			or_conditions.append(ip.price_list == selling_price_list)

		res = (
			qb.from_(ip)
			.select(ip.item_code, ip.price_list, ip.price_list_rate)
			.where(Criterion.all(and_conditions))
			.where(Criterion.any(or_conditions))
			.run(as_dict=True)
		)
		for x in res:
			price_list_map.update({(x.item_code, x.price_list): x.price_list_rate})

	return price_list_map


def get_data(filters=None):
	data = []
	customer_details = get_customer_details(filters)

	items = get_selling_items(filters)
	item_stock_map = frappe.get_all(
		"Bin", fields=["item_code", {"SUM": "actual_qty", "as": "available"}], group_by="item_code"
	)
	item_stock_map = {item.item_code: item.available for item in item_stock_map}
	price_list_map = fetch_item_prices(
		customer_details.customer,
		customer_details.price_list,
		customer_details.selling_price_list,
		items,
	)

	for item in items:
		price_list_rate = price_list_map.get(
			(item.item_code, customer_details.price_list or customer_details.selling_price_list), 0.0
		)
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

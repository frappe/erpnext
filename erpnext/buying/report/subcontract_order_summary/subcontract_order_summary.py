# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data


def get_data(report_filters):
	data = []
	orders = get_subcontracted_orders(report_filters)

	if orders:
		supplied_items = get_supplied_items(orders, report_filters)
		order_details = prepare_subcontracted_data(orders, supplied_items)
		get_subcontracted_data(order_details, data)

	return data


def get_subcontracted_orders(report_filters):
	fields = [
		"`tabSubcontracting Order Item`.`parent` as order_id",
		"`tabSubcontracting Order Item`.`item_code`",
		"`tabSubcontracting Order Item`.`item_name`",
		"`tabSubcontracting Order Item`.`qty`",
		"`tabSubcontracting Order Item`.`name`",
		"`tabSubcontracting Order Item`.`received_qty`",
		"`tabSubcontracting Order`.`status`",
	]

	filters = get_filters(report_filters)

	return frappe.get_all("Subcontracting Order", fields=fields, filters=filters) or []


def get_filters(report_filters):
	filters = [
		["Subcontracting Order", "docstatus", "=", 1],
		[
			"Subcontracting Order",
			"transaction_date",
			"between",
			(report_filters.from_date, report_filters.to_date),
		],
	]

	for field in ["name", "company"]:
		if report_filters.get(field):
			filters.append(["Subcontracting Order", field, "=", report_filters.get(field)])

	return filters


def get_supplied_items(orders, report_filters):
	if not orders:
		return []

	fields = [
		"parent",
		"main_item_code",
		"rm_item_code",
		"required_qty",
		"supplied_qty",
		"returned_qty",
		"total_supplied_qty",
		"consumed_qty",
		"reference_name",
	]

	filters = {"parent": ("in", [d.order_id for d in orders]), "docstatus": 1}

	supplied_items = {}
	for row in frappe.get_all("Subcontracting Order Supplied Item", fields=fields, filters=filters):
		new_key = (row.parent, row.reference_name, row.main_item_code)

		supplied_items.setdefault(new_key, []).append(row)

	return supplied_items


def prepare_subcontracted_data(orders, supplied_items):
	order_details = {}
	for row in orders:
		key = (row.order_id, row.name, row.item_code)
		if key not in order_details:
			order_details.setdefault(key, frappe._dict({"order_item": row, "supplied_items": []}))

		details = order_details[key]

		if supplied_items.get(key):
			for supplied_item in supplied_items[key]:
				details["supplied_items"].append(supplied_item)

	return order_details


def get_subcontracted_data(order_details, data):
	for _key, details in order_details.items():
		res = details.order_item
		for index, row in enumerate(details.supplied_items):
			if index != 0:
				res = {}

			res.update(row)
			data.append(res)


def get_columns(filters):
	return [
		{
			"label": _("Subcontract Order"),
			"fieldname": "order_id",
			"fieldtype": "Link",
			"options": "Subcontracting Order",
			"width": 100,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 80},
		{
			"label": _("Subcontracted Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{"label": _("Order Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("Received Qty"), "fieldname": "received_qty", "fieldtype": "Float", "width": 110},
		{
			"label": _("Supplied Item"),
			"fieldname": "rm_item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{"label": _("Required Qty"), "fieldname": "required_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Supplied Qty"), "fieldname": "supplied_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Consumed Qty"), "fieldname": "consumed_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Returned Qty"), "fieldname": "returned_qty", "fieldtype": "Float", "width": 110},
	]

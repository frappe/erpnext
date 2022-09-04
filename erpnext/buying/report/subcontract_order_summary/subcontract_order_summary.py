# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_data(report_filters):
	data = []
	orders = get_subcontracted_orders(report_filters)

	if orders:
		supplied_items = get_supplied_items(orders, report_filters)
		po_details = prepare_subcontracted_data(orders, supplied_items)
		get_subcontracted_data(po_details, data)

	return data


def get_subcontracted_orders(report_filters):
	fields = [
		"`tabPurchase Order Item`.`parent` as po_id",
		"`tabPurchase Order Item`.`item_code`",
		"`tabPurchase Order Item`.`item_name`",
		"`tabPurchase Order Item`.`qty`",
		"`tabPurchase Order Item`.`name`",
		"`tabPurchase Order Item`.`received_qty`",
		"`tabPurchase Order`.`status`",
	]

	filters = get_filters(report_filters)

	return frappe.get_all("Purchase Order", fields=fields, filters=filters) or []


def get_filters(report_filters):
	filters = [
		["Purchase Order", "docstatus", "=", 1],
		["Purchase Order", "is_subcontracted", "=", "Yes"],
		[
			"Purchase Order",
			"transaction_date",
			"between",
			(report_filters.from_date, report_filters.to_date),
		],
	]

	for field in ["name", "company"]:
		if report_filters.get(field):
			filters.append(["Purchase Order", field, "=", report_filters.get(field)])

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

	filters = {"parent": ("in", [d.po_id for d in orders]), "docstatus": 1}

	supplied_items = {}
	for row in frappe.get_all("Purchase Order Item Supplied", fields=fields, filters=filters):
		new_key = (row.parent, row.reference_name, row.main_item_code)

		supplied_items.setdefault(new_key, []).append(row)

	return supplied_items


def prepare_subcontracted_data(orders, supplied_items):
	po_details = {}
	for row in orders:
		key = (row.po_id, row.name, row.item_code)
		if key not in po_details:
			po_details.setdefault(key, frappe._dict({"po_item": row, "supplied_items": []}))

		details = po_details[key]

		if supplied_items.get(key):
			for supplied_item in supplied_items[key]:
				details["supplied_items"].append(supplied_item)

	return po_details


def get_subcontracted_data(po_details, data):
	for key, details in po_details.items():
		res = details.po_item
		for index, row in enumerate(details.supplied_items):
			if index != 0:
				res = {}

			res.update(row)
			data.append(res)


def get_columns():
	return [
		{
			"label": _("Purchase Order"),
			"fieldname": "po_id",
			"fieldtype": "Link",
			"options": "Purchase Order",
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

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_masters_condition


def execute(filters=None):
	return get_columns(), get_data()


def get_columns():
	return [
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 120,
		},
		{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 120},
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 150},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 120,
		},
		{"label": _("Balance Qty"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 140},
	]


def get_data():
	item = frappe.qb.DocType("Item")
	bin_table = frappe.qb.DocType("Bin")
	query = (
		frappe.qb.from_(item)
		.left_join(bin_table)
		.on(item.item_code == bin_table.item_code)
		.select(
			item.item_code,
			item.item_name,
			item.item_group,
			item.brand,
			item.description,
			bin_table.warehouse,
			bin_table.actual_qty,
		)
	)

	if condition := get_allowed_masters_condition(item.name, "Item"):
		query = query.where(condition)

	return query.run(as_dict=True)

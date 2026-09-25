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
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 120,
		},
		{"label": _("Actual"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 90},
		{"label": _("Requested"), "fieldname": "indented_qty", "fieldtype": "Float", "width": 90},
		{"label": _("Reserved"), "fieldname": "reserved_qty", "fieldtype": "Float", "width": 90},
		{"label": _("Ordered"), "fieldname": "ordered_qty", "fieldtype": "Float", "width": 90},
		{"label": _("Projected"), "fieldname": "projected_qty", "fieldtype": "Float", "width": 90},
	]


def get_data():
	bin_table = frappe.qb.DocType("Bin")
	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(bin_table)
		.inner_join(item)
		.on(bin_table.item_code == item.name)
		.select(
			bin_table.item_code,
			bin_table.warehouse,
			bin_table.actual_qty,
			bin_table.indented_qty,
			bin_table.reserved_qty,
			bin_table.ordered_qty,
			bin_table.projected_qty,
		)
		.where(bin_table.projected_qty < 0)
		.orderby(bin_table.projected_qty)
	)

	if condition := get_allowed_masters_condition(item.name, "Item"):
		query = query.where(condition)

	return query.run(as_dict=True)

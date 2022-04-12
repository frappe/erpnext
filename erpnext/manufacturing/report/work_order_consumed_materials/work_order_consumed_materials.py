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
	fields = get_fields()
	filters = get_filter_condition(report_filters)

	wo_items = {}
	for d in frappe.get_all("Work Order", filters=filters, fields=fields):
		d.extra_consumed_qty = 0.0
		if d.consumed_qty and d.consumed_qty > d.required_qty:
			d.extra_consumed_qty = d.consumed_qty - d.required_qty

		if d.extra_consumed_qty or not report_filters.show_extra_consumed_materials:
			wo_items.setdefault((d.name, d.production_item), []).append(d)

	data = []
	for key, wo_data in wo_items.items():
		for index, row in enumerate(wo_data):
			if index != 0:
				# If one work order has multiple raw materials then show parent data in the first row only
				for field in ["name", "status", "production_item", "qty", "produced_qty"]:
					row[field] = ""

			data.append(row)

	return data


def get_fields():
	return [
		"`tabWork Order Item`.`parent`",
		"`tabWork Order Item`.`item_code` as raw_material_item_code",
		"`tabWork Order Item`.`item_name` as raw_material_name",
		"`tabWork Order Item`.`required_qty`",
		"`tabWork Order Item`.`transferred_qty`",
		"`tabWork Order Item`.`consumed_qty`",
		"`tabWork Order`.`status`",
		"`tabWork Order`.`name`",
		"`tabWork Order`.`production_item`",
		"`tabWork Order`.`qty`",
		"`tabWork Order`.`produced_qty`",
	]


def get_filter_condition(report_filters):
	filters = {
		"docstatus": 1,
		"status": ("in", ["In Process", "Completed", "Stopped"]),
		"creation": ("between", [report_filters.from_date, report_filters.to_date]),
	}

	for field in ["name", "production_item", "company", "status"]:
		value = report_filters.get(field)
		if value:
			key = f"`{field}`"
			filters.update({key: value})

	return filters


def get_columns():
	return [
		{
			"label": _("Id"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 80,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 80},
		{
			"label": _("Production Item"),
			"fieldname": "production_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 130,
		},
		{"label": _("Qty to Produce"), "fieldname": "qty", "fieldtype": "Float", "width": 120},
		{"label": _("Produced Qty"), "fieldname": "produced_qty", "fieldtype": "Float", "width": 110},
		{
			"label": _("Raw Material Item"),
			"fieldname": "raw_material_item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("Item Name"), "fieldname": "raw_material_name", "width": 130},
		{"label": _("Required Qty"), "fieldname": "required_qty", "fieldtype": "Float", "width": 100},
		{
			"label": _("Transferred Qty"),
			"fieldname": "transferred_qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{"label": _("Consumed Qty"), "fieldname": "consumed_qty", "fieldtype": "Float", "width": 100},
		{
			"label": _("Extra Consumed Qty"),
			"fieldname": "extra_consumed_qty",
			"fieldtype": "Float",
			"width": 100,
		},
	]

# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	if not data:
		return [], [], None, []

	chart_data = get_chart_data(data)

	return columns, data, None, chart_data


def get_data(filters):
	bin = frappe.qb.DocType("Bin")
	wh = frappe.qb.DocType("Warehouse")
	item = frappe.qb.DocType("Item")

	query = (
		frappe.qb.from_(bin)
		.from_(wh)
		.from_(item)
		.select(
			bin.warehouse,
			bin.item_code,
			bin.actual_qty,
			bin.ordered_qty,
			bin.planned_qty,
			bin.reserved_qty,
			bin.reserved_qty_for_production,
			bin.projected_qty,
			wh.company,
			item.item_name,
			item.description,
		)
		.where(
			(item.disabled == 0)
			& (bin.projected_qty < 0)
			& (wh.name == bin.warehouse)
			& (bin.item_code == item.name)
		)
		.orderby(bin.projected_qty)
	)

	if filters.get("warehouse"):
		query = query.where(bin.warehouse.isin(filters.get("warehouse")))

	if filters.get("company"):
		query = query.where(wh.company == filters.get("company"))

	return query.run(as_dict=True)


def get_chart_data(data):
	labels, datapoints = [], []

	for row in data:
		labels.append(row.get("item_code"))
		datapoints.append(row.get("projected_qty"))

	if len(data) > 10:
		labels = labels[:10]
		datapoints = datapoints[:10]

	return {
		"data": {"labels": labels, "datasets": [{"name": _("Projected Qty"), "values": datapoints}]},
		"type": "bar",
	}


def get_columns():
	columns = [
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": _("Actual Quantity"),
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty",
		},
		{
			"label": _("Ordered Quantity"),
			"fieldname": "ordered_qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty",
		},
		{
			"label": _("Planned Quantity"),
			"fieldname": "planned_qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty",
		},
		{
			"label": _("Reserved Quantity"),
			"fieldname": "reserved_qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty",
		},
		{
			"label": _("Reserved Quantity for Production"),
			"fieldname": "reserved_qty_for_production",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty",
		},
		{
			"label": _("Projected Quantity"),
			"fieldname": "projected_qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty",
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 100},
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 120},
	]

	return columns

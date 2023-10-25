# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import copy

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import cint, date_diff, flt, getdate


def execute(filters=None):
	if not filters:
		return [], []

	validate_filters(filters)

	columns = get_columns(filters)
	data = get_data(filters)

	# prepare data for report and chart views
	data, chart_data = prepare_data(data, filters)

	return columns, data, None, chart_data


def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))


def get_data(filters):
	mr = frappe.qb.DocType("Material Request")
	mr_item = frappe.qb.DocType("Material Request Item")

	query = (
		frappe.qb.from_(mr)
		.join(mr_item)
		.on(mr_item.parent == mr.name)
		.select(
			mr.name.as_("material_request"),
			mr.transaction_date.as_("date"),
			mr_item.schedule_date.as_("required_date"),
			mr_item.item_code.as_("item_code"),
			Sum(Coalesce(mr_item.qty, 0)).as_("qty"),
			Sum(Coalesce(mr_item.stock_qty, 0)).as_("stock_qty"),
			Coalesce(mr_item.uom, "").as_("uom"),
			Coalesce(mr_item.stock_uom, "").as_("stock_uom"),
			Sum(Coalesce(mr_item.ordered_qty, 0)).as_("ordered_qty"),
			Sum(Coalesce(mr_item.received_qty, 0)).as_("received_qty"),
			(Sum(Coalesce(mr_item.stock_qty, 0)) - Sum(Coalesce(mr_item.received_qty, 0))).as_(
				"qty_to_receive"
			),
			Sum(Coalesce(mr_item.received_qty, 0)).as_("received_qty"),
			(Sum(Coalesce(mr_item.stock_qty, 0)) - Sum(Coalesce(mr_item.ordered_qty, 0))).as_(
				"qty_to_order"
			),
			mr_item.item_name,
			mr_item.description,
			mr.company,
		)
		.where(
			(mr.material_request_type == "Purchase")
			& (mr.docstatus == 1)
			& (mr.status != "Stopped")
			& (mr.per_received < 100)
		)
	)

	query = get_conditions(filters, query, mr, mr_item)  # add conditional conditions

	query = query.groupby(mr.name, mr_item.item_code).orderby(mr.transaction_date, mr.schedule_date)
	data = query.run(as_dict=True)
	return data


def get_conditions(filters, query, mr, mr_item):
	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(
			(mr.transaction_date >= filters.get("from_date"))
			& (mr.transaction_date <= filters.get("to_date"))
		)
	if filters.get("company"):
		query = query.where(mr.company == filters.get("company"))

	if filters.get("material_request"):
		query = query.where(mr.name == filters.get("material_request"))

	if filters.get("item_code"):
		query = query.where(mr_item.item_code == filters.get("item_code"))

	return query


def update_qty_columns(row_to_update, data_row):
	fields = ["qty", "stock_qty", "ordered_qty", "received_qty", "qty_to_receive", "qty_to_order"]
	for field in fields:
		row_to_update[field] += flt(data_row[field])


def prepare_data(data, filters):
	"""Prepare consolidated Report data and Chart data"""
	material_request_map, item_qty_map = {}, {}
	precision = cint(frappe.db.get_default("float_precision")) or 2

	for row in data:
		# item wise map for charts
		if not row["item_code"] in item_qty_map:
			item_qty_map[row["item_code"]] = {
				"qty": flt(row["stock_qty"], precision),
				"stock_qty": flt(row["stock_qty"], precision),
				"stock_uom": row["stock_uom"],
				"uom": row["uom"],
				"ordered_qty": flt(row["ordered_qty"], precision),
				"received_qty": flt(row["received_qty"], precision),
				"qty_to_receive": flt(row["qty_to_receive"], precision),
				"qty_to_order": flt(row["qty_to_order"], precision),
			}
		else:
			item_entry = item_qty_map[row["item_code"]]
			update_qty_columns(item_entry, row)

		if filters.get("group_by_mr"):
			# consolidated material request map for group by filter
			if not row["material_request"] in material_request_map:
				# create an entry with mr as key
				row_copy = copy.deepcopy(row)
				material_request_map[row["material_request"]] = row_copy
			else:
				mr_row = material_request_map[row["material_request"]]
				mr_row["required_date"] = min(getdate(mr_row["required_date"]), getdate(row["required_date"]))

				# sum numeric columns
				update_qty_columns(mr_row, row)

	chart_data = prepare_chart_data(item_qty_map)

	if filters.get("group_by_mr"):
		data = []
		for mr in material_request_map:
			data.append(material_request_map[mr])
		return data, chart_data

	return data, chart_data


def prepare_chart_data(item_data):
	labels, qty_to_order, ordered_qty, received_qty, qty_to_receive = [], [], [], [], []

	if len(item_data) > 30:
		item_data = dict(list(item_data.items())[:30])

	for row in item_data:
		mr_row = item_data[row]
		labels.append(row)
		qty_to_order.append(mr_row["qty_to_order"])
		ordered_qty.append(mr_row["ordered_qty"])
		received_qty.append(mr_row["received_qty"])
		qty_to_receive.append(mr_row["qty_to_receive"])

	chart_data = {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Qty to Order"), "values": qty_to_order},
				{"name": _("Ordered Qty"), "values": ordered_qty},
				{"name": _("Received Qty"), "values": received_qty},
				{"name": _("Qty to Receive"), "values": qty_to_receive},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}

	return chart_data


def get_columns(filters):
	columns = [
		{
			"label": _("Material Request"),
			"fieldname": "material_request",
			"fieldtype": "Link",
			"options": "Material Request",
			"width": 150,
		},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 90},
		{"label": _("Required By"), "fieldname": "required_date", "fieldtype": "Date", "width": 100},
	]

	if not filters.get("group_by_mr"):
		columns.extend(
			[
				{
					"label": _("Item Code"),
					"fieldname": "item_code",
					"fieldtype": "Link",
					"options": "Item",
					"width": 100,
				},
				{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 100},
				{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 200},
				{
					"label": _("UOM"),
					"fieldname": "uom",
					"fieldtype": "Data",
					"width": 100,
				},
				{
					"label": _("Stock UOM"),
					"fieldname": "stock_uom",
					"fieldtype": "Data",
					"width": 100,
				},
			]
		)

	columns.extend(
		[
			{
				"label": _("Qty"),
				"fieldname": "qty",
				"fieldtype": "Float",
				"width": 140,
				"convertible": "qty",
			},
			{
				"label": _("Qty in Stock UOM"),
				"fieldname": "stock_qty",
				"fieldtype": "Float",
				"width": 140,
				"convertible": "qty",
			},
			{
				"label": _("Ordered Qty"),
				"fieldname": "ordered_qty",
				"fieldtype": "Float",
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Received Qty"),
				"fieldname": "received_qty",
				"fieldtype": "Float",
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Qty to Receive"),
				"fieldname": "qty_to_receive",
				"fieldtype": "Float",
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Qty to Order"),
				"fieldname": "qty_to_order",
				"fieldtype": "Float",
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Company"),
				"fieldname": "company",
				"fieldtype": "Link",
				"options": "Company",
				"width": 100,
			},
		]
	)

	return columns

# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import copy

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate


def execute(filters=None):
	if not filters:
		return [],[]

	validate_filters(filters)

	columns = get_columns(filters)
	conditions = get_conditions(filters)

	#get queried data
	data = get_data(filters, conditions)

	#prepare data for report and chart views
	data, chart_data = prepare_data(data, filters)

	return columns, data, None, chart_data

def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))

def get_conditions(filters):
	conditions = ''

	if filters.get("from_date") and filters.get("to_date"):
		conditions += " and mr.transaction_date between '{0}' and '{1}'".format(filters.get("from_date"),filters.get("to_date"))

	if filters.get("company"):
		conditions += " and mr.company = '{0}'".format(filters.get("company"))

	if filters.get("material_request"):
		conditions += " and mr.name = '{0}'".format(filters.get("material_request"))

	if filters.get("item_code"):
		conditions += " and mr_item.item_code = '{0}'".format(filters.get("item_code"))

	return conditions

def get_data(filters, conditions):
	data = frappe.db.sql("""
		select
			mr.name as material_request,
			mr.transaction_date as date,
			mr_item.schedule_date as required_date,
			mr_item.item_code as item_code,
			sum(ifnull(mr_item.stock_qty, 0)) as qty,
			ifnull(mr_item.stock_uom, '') as uom,
			sum(ifnull(mr_item.ordered_qty, 0)) as ordered_qty,
			sum(ifnull(mr_item.received_qty, 0)) as received_qty,
			(sum(ifnull(mr_item.stock_qty, 0)) - sum(ifnull(mr_item.received_qty, 0))) as qty_to_receive,
			(sum(ifnull(mr_item.stock_qty, 0)) - sum(ifnull(mr_item.ordered_qty, 0))) as qty_to_order,
			mr_item.item_name as item_name,
			mr_item.description as "description",
			mr.company as company
		from
			`tabMaterial Request` mr, `tabMaterial Request Item` mr_item
		where
			mr_item.parent = mr.name
			and mr.material_request_type = "Purchase"
			and mr.docstatus = 1
			and mr.status != "Stopped"
			{conditions}
		group by mr.name, mr_item.item_code
		having
			sum(ifnull(mr_item.ordered_qty, 0)) < sum(ifnull(mr_item.stock_qty, 0))
		order by mr.transaction_date, mr.schedule_date""".format(conditions=conditions), as_dict=1)

	return data

def update_qty_columns(row_to_update, data_row):
	fields = ["qty", "ordered_qty", "received_qty", "qty_to_receive", "qty_to_order"]
	for field in fields:
		row_to_update[field] += flt(data_row[field])

def prepare_data(data, filters):
	"""Prepare consolidated Report data and Chart data"""
	material_request_map, item_qty_map = {}, {}

	for row in data:
		# item wise map for charts
		if not row["item_code"] in item_qty_map:
			item_qty_map[row["item_code"]] = {
				"qty" : row["qty"],
				"ordered_qty" : row["ordered_qty"],
				"received_qty": row["received_qty"],
				"qty_to_receive": row["qty_to_receive"],
				"qty_to_order" : row["qty_to_order"],
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

				#sum numeric columns
				update_qty_columns(mr_row, row)

	chart_data = prepare_chart_data(item_qty_map)

	if filters.get("group_by_mr"):
		data =[]
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
		"data" : {
			"labels": labels,
			"datasets": [
				{
					'name': _('Qty to Order'),
					'values': qty_to_order
				},
				{
					'name': _('Ordered Qty'),
					'values': ordered_qty
				},
				{
					'name': _('Received Qty'),
					'values': received_qty
				},
				{
					'name': _('Qty to Receive'),
					'values': qty_to_receive
				}
			]
		},
		"type": "bar",
		"barOptions": {
			"stacked": 1
		},
	}

	return chart_data

def get_columns(filters):
	columns = [
		{
			"label": _("Material Request"),
			"fieldname": "material_request",
			"fieldtype": "Link",
			"options": "Material Request",
			"width": 150
		},
		{
			"label":_("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 90
		},
		{
			"label":_("Required By"),
			"fieldname": "required_date",
			"fieldtype": "Date",
			"width": 100
		}
	]

	if not filters.get("group_by_mr"):
		columns.extend([{
			"label":_("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100
		},
		{
			"label":_("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Stock UOM"),
			"fieldname": "uom",
			"fieldtype": "Data",
			"width": 100,
		}])

	columns.extend([
		{
			"label": _("Stock Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty"
		},
		{
			"label": _("Ordered Qty"),
			"fieldname": "ordered_qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty"
		},
		{
			"label": _("Received Qty"),
			"fieldname": "received_qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty"
		},
		{
			"label": _("Qty to Receive"),
			"fieldname": "qty_to_receive",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty"
		},
		{
			"label": _("Qty to Order"),
			"fieldname": "qty_to_order",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty"
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 100
		}
	])

	return columns

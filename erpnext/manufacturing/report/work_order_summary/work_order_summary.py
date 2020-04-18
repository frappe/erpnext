# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import date_diff, today
from frappe import _

def execute(filters=None):
	columns, data = [], []

	if not filters.get("age"):
		filters["age"] = 0

	data = get_data(filters)
	columns = get_columns(filters)
	chart_data = get_chart_data(data, filters)
	return columns, data, None, chart_data

def get_data(filters):
	query_filters = {"docstatus": 1}

	fields = ["name", "status", "sales_order", "production_item", "qty", "produced_qty",
		"planned_start_date", "planned_end_date", "actual_start_date", "actual_end_date", "lead_time"]

	for field in ["sales_order", "production_item", "status", "company"]:
		if filters.get(field):
			query_filters[field] = ("in", filters.get(field))

	query_filters["planned_start_date"] = (">=", filters.get("from_date"))
	query_filters["planned_end_date"] = ("<=", filters.get("to_date"))

	data = frappe.get_all("Work Order",
		fields= fields, filters=query_filters, order_by="planned_start_date asc")

	res = []
	for d in data:
		start_date = d.actual_start_date or d.planned_start_date
		d.age = 0

		if d.status != 'Completed':
			d.age = date_diff(today(), start_date)

		if filters.get("age") <= d.age:
			res.append(d)

	return res

def get_chart_data(periodic_data, columns):
	labels = ["Not Started", "In Process", "Stopped", "Completed"]

	status_wise_data = {
		"Not Started": 0,
		"In Process": 0,
		"Stopped": 0,
		"Completed": 0
	}

	for d in periodic_data:
		if d.status == "In Process" and d.produced_qty:
			status_wise_data["Completed"] += d.produced_qty

		status_wise_data[d.status] += d.qty

	values = [status_wise_data["Not Started"], status_wise_data["In Process"],
		status_wise_data["Stopped"], status_wise_data["Completed"]]

	chart = {
		"data": {
			'labels': labels,
			'datasets': [{'name':'Qty Wise Chart', 'values': values}]
		},
		"type": "donut",
		"height": 300,
		"colors": ["#ff5858", "#ffa00a", "#5e64ff", "#98d85b"]
	}

	return chart

def get_columns(filters):
	columns = [
		{
			"label": _("Id"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 100
		},
	]

	if not filters.get("status"):
		columns.append(
			{
				"label": _("Status"),
				"fieldname": "status",
				"width": 100
			},
		)

	columns.extend([
		{
			"label": _("Production Item"),
			"fieldname": "production_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 130
		},
		{
			"label": _("Produce Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 110
		},
		{
			"label": _("Produced Qty"),
			"fieldname": "produced_qty",
			"fieldtype": "Float",
			"width": 110
		},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 90
		},
		{
			"label": _("Planned Start Date"),
			"fieldname": "planned_start_date",
			"fieldtype": "Date",
			"width": 150
		},
		{
			"label": _("Planned End Date"),
			"fieldname": "planned_end_date",
			"fieldtype": "Date",
			"width": 150
		}
	])

	if filters.get("status") != 'Not Started':
		columns.extend([
			{
				"label": _("Actual Start Date"),
				"fieldname": "actual_start_date",
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Actual End Date"),
				"fieldname": "actual_end_date",
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Age"),
				"fieldname": "age",
				"fieldtype": "Float",
				"width": 110
			},
		])

	if filters.get("status") == 'Completed':
		columns.extend([
			{
				"label": _("Lead Time (in mins)"),
				"fieldname": "lead_time",
				"fieldtype": "Float",
				"width": 110
			},
		])

	return columns
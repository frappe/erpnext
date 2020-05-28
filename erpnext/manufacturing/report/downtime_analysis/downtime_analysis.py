# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	chart_data = get_chart_data(data, filters)
	return columns, data, None, chart_data

def get_data(filters):
	query_filters = {}

	fields = ["name", "workstation", "operator", "from_time", "to_time", "downtime", "stop_reason", "remarks"]

	query_filters["from_time"] = (">=", filters.get("from_date"))
	query_filters["to_time"] = ("<=", filters.get("to_date"))

	if filters.get("workstation"):
		query_filters["workstation"] = filters.get("workstation")

	data = frappe.get_all("Downtime Entry", fields= fields, filters=query_filters) or []
	for d in data:
		if d.downtime:
			d.downtime = d.downtime / 60

	return data

def get_chart_data(data, columns):
	labels = sorted(list(set([d.workstation for d in data])))

	workstation_wise_data = {}
	for d in data:
		if d.workstation not in workstation_wise_data:
			workstation_wise_data[d.workstation] = 0

		workstation_wise_data[d.workstation] += flt(d.downtime, 2)

	datasets = []
	for label in labels:
		datasets.append(workstation_wise_data.get(label, 0))

	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": "Machine Downtime", "values": datasets}
			]
		},
		"type": "bar"
	}

	return chart

def get_columns(filters):
	return [
		{
			"label": _("ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Downtime Entry",
			"width": 100
		},
		{
			"label": _("Machine"),
			"fieldname": "workstation",
			"fieldtype": "Link",
			"options": "Workstation",
			"width": 100
		},
		{
			"label": _("Operator"),
			"fieldname": "operator",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130
		},
		{
			"label": _("From Time"),
			"fieldname": "from_time",
			"fieldtype": "Datetime",
			"width": 160
		},
		{
			"label": _("To Time"),
			"fieldname": "to_time",
			"fieldtype": "Datetime",
			"width": 160
		},
		{
			"label": _("Downtime (In Hours)"),
			"fieldname": "downtime",
			"fieldtype": "Float",
			"width": 150
		},
		{
			"label": _("Stop Reason"),
			"fieldname": "stop_reason",
			"fieldtype": "Data",
			"width": 220
		},
		{
			"label": _("Remarks"),
			"fieldname": "remarks",
			"fieldtype": "Text",
			"width": 100
		}
	]
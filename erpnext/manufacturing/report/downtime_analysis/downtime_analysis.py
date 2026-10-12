# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, get_datetime, time_diff_in_hours


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	chart_data = get_chart_data(data, filters)
	return columns, data, None, chart_data


def get_data(filters):
	query_filters = {}

	fields = [
		"name",
		"workstation",
		"operator",
		"from_time",
		"to_time",
		"downtime",
		"stop_reason",
		"remarks",
	]

	from_date = get_datetime(filters.get("from_date"))
	to_date = get_datetime(filters.get("to_date"))
	query_filters["from_time"] = ("<", to_date)
	query_filters["to_time"] = (">", from_date)

	if filters.get("workstation"):
		query_filters["workstation"] = filters.get("workstation")

	data = frappe.get_list("Downtime Entry", fields=fields, filters=query_filters, limit_page_length=0) or []
	for d in data:
		d.downtime = time_diff_in_hours(
			min(get_datetime(d.to_time), to_date), max(get_datetime(d.from_time), from_date)
		)

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
		"data": {"labels": labels, "datasets": [{"name": "Machine Downtime", "values": datasets}]},
		"type": "bar",
	}

	return chart


def get_columns(filters):
	return [
		{
			"label": _("ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Downtime Entry",
			"width": 100,
		},
		{
			"label": _("Machine"),
			"fieldname": "workstation",
			"fieldtype": "Link",
			"options": "Workstation",
			"width": 100,
		},
		{
			"label": _("Operator"),
			"fieldname": "operator",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{"label": _("From Time"), "fieldname": "from_time", "fieldtype": "Datetime", "width": 160},
		{"label": _("To Time"), "fieldname": "to_time", "fieldtype": "Datetime", "width": 160},
		{"label": _("Downtime (In Hours)"), "fieldname": "downtime", "fieldtype": "Float", "width": 150},
		{"label": _("Stop Reason"), "fieldname": "stop_reason", "fieldtype": "Data", "width": 220},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Text", "width": 100},
	]

# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	chart_data = get_chart_data(data, filters)
	return columns, data , None, chart_data

def get_data(filters):
	query_filters = {"docstatus": ("<", 2)}

	fields = ["name", "status", "report_date", "item_code", "item_name", "sample_size",
		"inspection_type", "reference_type", "reference_name", "inspected_by"]

	for field in ["status", "item_code", "status", "inspected_by"]:
		if filters.get(field):
			query_filters[field] = ("in", filters.get(field))

	query_filters["report_date"] = (">=", filters.get("from_date"))
	query_filters["report_date"] = ("<=", filters.get("to_date"))

	return frappe.get_all("Quality Inspection",
		fields= fields, filters=query_filters, order_by="report_date asc")

def get_chart_data(periodic_data, columns):
	labels = ["Rejected", "Accepted"]

	status_wise_data = {
		"Accepted": 0,
		"Rejected": 0
	}

	datasets = []

	for d in periodic_data:
		status_wise_data[d.status] += 1

	datasets.append({'name':'Qty Wise Chart',
		'values': [status_wise_data.get("Rejected"), status_wise_data.get("Accepted")]})

	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		},
		"type": "donut",
		"height": 300
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
		{
			"label": _("Report Date"),
			"fieldname": "report_date",
			"fieldtype": "Date",
			"width": 150
		}
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
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 130
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Sample Size"),
			"fieldname": "sample_size",
			"fieldtype": "Float",
			"width": 110
		},
		{
			"label": _("Inspection Type"),
			"fieldname": "inspection_type",
			"fieldtype": "Data",
			"width": 110
		},
		{
			"label": _("Document Type"),
			"fieldname": "reference_type",
			"fieldtype": "Data",
			"width": 90
		},
		{
			"label": _("Document Name"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_type",
			"width": 150
		},
		{
			"label": _("Inspected By"),
			"fieldname": "inspected_by",
			"fieldtype": "Link",
			"options": "User",
			"width": 150
		}
	])

	return columns
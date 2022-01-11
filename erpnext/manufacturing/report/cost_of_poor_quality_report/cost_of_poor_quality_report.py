# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns, data = [], []

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_data(report_filters):
	data = []
	operations = frappe.get_all("Operation", filters = {"is_corrective_operation": 1})
	if operations:
		operations = [d.name for d in operations]
		fields = ["production_item as item_code", "item_name", "work_order", "operation",
			"workstation", "total_time_in_mins", "name", "hour_rate", "serial_no", "batch_no"]

		filters = get_filters(report_filters, operations)

		job_cards = frappe.get_all("Job Card", fields = fields,
			filters = filters)

		for row in job_cards:
			row.operating_cost = flt(row.hour_rate) * (flt(row.total_time_in_mins) / 60.0)
			data.append(row)

	return data

def get_filters(report_filters, operations):
	filters = {"docstatus": 1, "operation": ("in", operations), "is_corrective_job_card": 1}
	for field in ["name", "work_order", "operation", "workstation", "company", "serial_no", "batch_no", "production_item"]:
		if report_filters.get(field):
			if field != 'serial_no':
				filters[field] = report_filters.get(field)
			else:
				filters[field] = ('like', '% {} %'.format(report_filters.get(field)))

	return filters

def get_columns(filters):
	return [
		{
			"label": _("Job Card"),
			"fieldtype": "Link",
			"fieldname": "name",
			"options": "Job Card",
			"width": "120"
		},
		{
			"label": _("Work Order"),
			"fieldtype": "Link",
			"fieldname": "work_order",
			"options": "Work Order",
			"width": "100"
		},
		{
			"label": _("Item Code"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"options": "Item",
			"width": "100"
		},
		{
			"label": _("Item Name"),
			"fieldtype": "Data",
			"fieldname": "item_name",
			"width": "100"
		},
		{
			"label": _("Operation"),
			"fieldtype": "Link",
			"fieldname": "operation",
			"options": "Operation",
			"width": "100"
		},
		{
			"label": _("Serial No"),
			"fieldtype": "Data",
			"fieldname": "serial_no",
			"width": "100"
		},
		{
			"label": _("Batch No"),
			"fieldtype": "Data",
			"fieldname": "batch_no",
			"width": "100"
		},
		{
			"label": _("Workstation"),
			"fieldtype": "Link",
			"fieldname": "workstation",
			"options": "Workstation",
			"width": "100"
		},
		{
			"label": _("Operating Cost"),
			"fieldtype": "Currency",
			"fieldname": "operating_cost",
			"width": "150"
		},
		{
			"label": _("Total Time (in Mins)"),
			"fieldtype": "Float",
			"fieldname": "total_time_in_mins",
			"width": "150"
		}
	]

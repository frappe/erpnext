# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
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
			"workstation", "total_time_in_mins", "name", "hour_rate"]

		filters = get_filters(report_filters, operations)

		job_cards = frappe.get_all("Job Card", fields = fields,
			filters = filters)

		for row in job_cards:
			row.operating_cost = flt(row.hour_rate) * (flt(row.total_time_in_mins) / 60.0)
			update_raw_material_cost(row, report_filters)
			update_time_details(row, report_filters, data)

	return data

def get_filters(report_filters, operations):
	filters = {"docstatus": 1, "operation": ("in", operations), "is_corrective_job_card": 1}
	for field in ["name", "work_order", "operation", "workstation", "company"]:
		if report_filters.get(field):
			filters[field] = report_filters.get(field)

	return filters

def update_raw_material_cost(row, filters):
	row.rm_cost = 0.0
	for data in frappe.get_all("Job Card Item", fields = ["amount"],
		filters={"parent": row.name, "docstatus": 1}):
		row.rm_cost += data.amount

def update_time_details(row, filters, data):
	args = frappe._dict({"item_code": "", "item_name": "", "name": "", "work_order":"",
		"operation": "", "workstation":"", "operating_cost": "", "rm_cost": "", "total_time_in_mins": ""})

	i=0
	for time_log in frappe.get_all("Job Card Time Log",
		fields = ["from_time", "to_time", "time_in_mins"],
		filters={"parent": row.name, "docstatus": 1,
			"from_time": (">=", filters.from_date), "to_time": ("<=", filters.to_date)}):

		if i==0:
			i += 1
			row.update(time_log)
			data.append(row)
		else:
			args.update(time_log)
			data.append(args)

def get_columns(filters):
	return [
		{
			"label": _("Job Card"),
			"fieldtype": "Link",
			"fieldname": "name",
			"options": "Job Card",
			"width": "100"
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
			"width": "100"
		},
		{
			"label": _("Raw Material Cost"),
			"fieldtype": "Currency",
			"fieldname": "rm_cost",
			"width": "100"
		},
		{
			"label": _("Total Time (in Mins)"),
			"fieldtype": "Float",
			"fieldname": "total_time_in_mins",
			"width": "100"
		},
		{
			"label": _("From Time"),
			"fieldtype": "Datetime",
			"fieldname": "from_time",
			"width": "100"
		},
		{
			"label": _("To Time"),
			"fieldtype": "Datetime",
			"fieldname": "to_time",
			"width": "100"
		},
		{
			"label": _("Time in Mins"),
			"fieldtype": "Float",
			"fieldname": "time_in_mins",
			"width": "100"
		},
	]
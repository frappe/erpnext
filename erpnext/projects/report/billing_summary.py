# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import time_diff_in_hours

def get_columns():
	return [
		{
			"label": _("Employee ID"),
			"fieldtype": "Link",
			"fieldname": "employee",
			"options": "Employee",
			"width": 300
		},
		{
			"label": _("Employee Name"),
			"fieldtype": "data",
			"fieldname": "employee_name",
			"hidden": 1,
			"width": 200
		},
		{
			"label": _("Timesheet"),
			"fieldtype": "Link",
			"fieldname": "timesheet",
			"options": "Timesheet",
			"width": 150
		},
		{
			"label": _("Billable Hours"),
			"fieldtype": "Float",
			"fieldname": "total_billable_hours",
			"width": 50
		},
		{
			"label": _("Working Hours"),
			"fieldtype": "Float",
			"fieldname": "total_hours",
			"width": 50
		},
		{
			"label": _("Amount"),
			"fieldtype": "Currency",
			"fieldname": "amount",
			"width": 100
		}
	]

def get_data(filters):
	data = []
	record = get_records(filters)

	for entries in record:
		total_hours = 0
		total_billable_hours = 0
		total_amount = 0
		entries_exists = False
		timesheet_details = get_timesheet_details(filters, entries.name)

		for activity in timesheet_details:
			entries_exists = True
			time_start = activity.from_time
			time_end = frappe.utils.add_to_date(activity.from_time, hours=activity.hours)
			from_date = frappe.utils.get_datetime(filters.from_date)
			to_date = frappe.utils.get_datetime(filters.to_date)

			if time_start <= from_date and time_end >= from_date:
				total_hours, total_billable_hours, total_amount = get_billable_and_total_hours(activity,
					time_end, from_date, total_hours, total_billable_hours, total_amount)
			elif time_start <= to_date and time_end >= to_date:
				total_hours, total_billable_hours, total_amount = get_billable_and_total_hours(activity,
					to_date, time_start, total_hours, total_billable_hours, total_amount)
			elif time_start >= from_date and time_end <= to_date:
				total_hours, total_billable_hours, total_amount = get_billable_and_total_hours(activity,
					time_end, time_start, total_hours, total_billable_hours, total_amount)

		row = {
			"employee": entries.employee,
			"employee_name": entries.employee_name,
			"timesheet": entries.name,
			"total_billable_hours": total_billable_hours,
			"total_hours": total_hours,
			"amount": total_amount
		}
		if entries_exists:
			data.append(row)
			entries_exists = False
	return data

def get_records(filters):
	record_filters = [
			["start_date", "<=", filters.to_date],
			["end_date", ">=", filters.from_date],
			["docstatus", "=", 1]
		]

	if "employee" in filters:
		record_filters.append(["employee", "=", filters.employee])

	return frappe.get_all("Timesheet", filters=record_filters, fields=[" * "] )

def get_billable_and_total_hours(activity, end, start, total_hours, total_billable_hours, total_amount):
	total_hours += abs(time_diff_in_hours(end, start))
	if activity.billable:
		total_billable_hours += abs(time_diff_in_hours(end, start))
		total_amount += total_billable_hours * activity.billing_rate
	return total_hours, total_billable_hours, total_amount

def get_timesheet_details(filters, parent):
	timesheet_details_filter = {"parent": parent}

	if "project" in filters:
		timesheet_details_filter["project"] = filters.project

	return frappe.get_all(
		"Timesheet Detail",
		filters = timesheet_details_filter,
		fields=["*"]
		)

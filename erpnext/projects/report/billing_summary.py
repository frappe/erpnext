# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import time_diff_in_hours, flt

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
			"label": _("Working Hours"),
			"fieldtype": "Float",
			"fieldname": "total_hours",
			"width": 150
		},
		{
			"label": _("Billable Hours"),
			"fieldtype": "Float",
			"fieldname": "total_billable_hours",
			"width": 150
		},
		{
			"label": _("Billing Amount"),
			"fieldtype": "Currency",
			"fieldname": "amount",
			"width": 150
		}
	]

def get_data(filters):
	data = []
	if(filters.from_date > filters.to_date):
		frappe.msgprint(_(" From Date can not be greater than To Date"))
		return data

	timesheets = get_timesheets(filters)

	filters.from_date = frappe.utils.get_datetime(filters.from_date)
	filters.to_date = frappe.utils.add_to_date(frappe.utils.get_datetime(filters.to_date), days=1, seconds=-1)

	timesheet_details = get_timesheet_details(filters, timesheets.keys())

	for ts, ts_details in timesheet_details.items():
		total_hours = 0
		total_billing_hours = 0
		total_amount = 0

		for row in ts_details:
			from_time, to_time = filters.from_date, filters.to_date

			if row.to_time < from_time or row.from_time > to_time:
				continue

			if row.from_time > from_time:
				from_time = row.from_time

			if row.to_time < to_time:
				to_time = row.to_time

			activity_duration, billing_duration = get_billable_and_total_duration(row, from_time, to_time)

			total_hours += activity_duration
			total_billing_hours += billing_duration
			total_amount += billing_duration * flt(row.billing_rate)

		if total_hours:
			data.append({
				"employee": timesheets.get(ts).employee,
				"employee_name": timesheets.get(ts).employee_name,
				"timesheet": ts,
				"total_billable_hours": total_billing_hours,
				"total_hours": total_hours,
				"amount": total_amount
			})

	return data

def get_timesheets(filters):
	record_filters = [
			["start_date", "<=", filters.to_date],
			["end_date", ">=", filters.from_date],
			["docstatus", "=", 1]
		]

	if "employee" in filters:
		record_filters.append(["employee", "=", filters.employee])

	timesheets = frappe.get_all("Timesheet", filters=record_filters, fields=["employee", "employee_name", "name"])
	timesheet_map = frappe._dict()
	for d in timesheets:
		timesheet_map.setdefault(d.name, d)

	return timesheet_map

def get_timesheet_details(filters, timesheet_list):
	timesheet_details_filter = {
		"parent": ["in", timesheet_list]
	}

	if "project" in filters:
		timesheet_details_filter["project"] = filters.project

	timesheet_details = frappe.get_all(
		"Timesheet Detail",
		filters = timesheet_details_filter,
		fields=["from_time", "to_time", "hours", "billable", "billing_hours", "billing_rate", "parent"]
	)

	timesheet_details_map = frappe._dict()
	for d in timesheet_details:
		timesheet_details_map.setdefault(d.parent, []).append(d)

	return timesheet_details_map

def get_billable_and_total_duration(activity, start_time, end_time):
	precision = frappe.get_precision("Timesheet Detail", "hours")
	activity_duration = time_diff_in_hours(end_time, start_time)
	billing_duration = 0.0
	if activity.billable:
		billing_duration = activity.billing_hours
		if activity_duration != activity.billing_hours:
			billing_duration = activity_duration * activity.billing_hours / activity.hours

	return flt(activity_duration, precision), flt(billing_duration, precision)
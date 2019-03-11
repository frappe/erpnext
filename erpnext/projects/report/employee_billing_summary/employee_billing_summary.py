# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import time_diff_in_hours

def execute(filters=None):
	filters = frappe._dict(filters or {})
	print(filters)

	columns = get_columns()

	data = get_data(filters)
	return columns, data

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
			"label": _("Date"),
			"fieldtype": "Date",
			"fieldname": "date",
			"width": 150
		},
		{
			"label": _("Total Billable Hours"),
			"fieldtype": "Int",
			"fieldname": "total_billable_hours",
			"width": 50
		},
		{
			"label": _("Total Hours"),
			"fieldtype": "Int",
			"fieldname": "total_hours",
			"width": 50
		},
		{
			"label": _("Amount"),
			"fieldtype": "Int",
			"fieldname": "amount",
			"width": 50
		}
	]

def get_data(filters):
	data = []
	if "employee" in filters:
		record= frappe.db.sql('''SELECT
				employee, employee_name, name, total_billable_hours, total_hours, total_billable_amount
			FROM
				`tabTimesheet`
			WHERE
				employee = %s and (start_date <= %s and end_date >= %s)''',(filters.employee, filters.to_date, filters.from_date),
			as_dict=1
		)
		for entries in record:

			timesheet_details = frappe.get_all(
				"Timesheet Detail",
				filters={"parent": entries.name},
				fields=["*"]
				)

			total_hours = 0
			total_billable_hours = 0
			print("-------------------------------------------->>>>>>>")
			for time in timesheet_details:
				time_start = time.from_time
				time_end = frappe.utils.add_to_date(time.from_time, hours=time.hours)

				from_date = frappe.utils.get_datetime(filters.from_date)
				to_date = frappe.utils.get_datetime(filters.to_date)

				if time_start <= from_date and time_end <= to_date:
					total_hours += abs(time_diff_in_hours(time_end, from_date))
					print(from_date, time_end)
					print("case 1", entries.name,time_diff_in_hours(time_end, from_date))
				elif time_start >= from_date and time_end >= to_date:
					total_hours += abs(time_diff_in_hours(to_date, time_start))
					print(time_start, to_date)
					print("case 2", entries.name,time_diff_in_hours(to_date, time_start))
				elif time_start >= from_date and time_end <= to_date:
					total_hours = entries.total_hours
					print("case 3 all set", entries.name)

			print(total_hours)
			print("-------------------------------------------->>>>>>>")
			row = {
				"employee": entries.employee,
				"employee_name": entries.employee_name,
				"timesheet": entries.name,
				"total_billable_hours": entries.total_billable_hours,
				"total_hours": entries.total_hours,
				"amount": 1
			}
			data.append(row)
	return data
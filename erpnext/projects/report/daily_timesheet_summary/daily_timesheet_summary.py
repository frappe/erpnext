# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_days, getdate

from erpnext.stock.utils import get_combine_datetime


def execute(filters=None):
	filters = filters or {}

	columns = get_column()
	data = get_data(filters)

	return columns, data


def get_column():
	return [
		_("Timesheet") + ":Link/Timesheet:120",
		_("Employee") + "::150",
		_("Employee Name") + "::150",
		_("From Datetime") + "::140",
		_("To Datetime") + "::140",
		_("Hours") + "::70",
		_("Activity Type") + "::120",
		_("Task") + ":Link/Task:150",
		_("Project") + ":Link/Project:120",
		_("Status") + "::70",
	]


def get_data(filters):
	ts = frappe.qb.DocType("Timesheet")
	tsd = frappe.qb.DocType("Timesheet Detail")

	# Base the query on Timesheet so get_query applies its user-permission match conditions
	# (the qb form of build_match_conditions); Timesheet Detail rows are inner-joined on.
	query = (
		frappe.qb.get_query(
			"Timesheet",
			fields=["name", "employee", "employee_name"],
			ignore_permissions=False,
		)
		.inner_join(tsd)
		.on(tsd.parent == ts.name)
		.select(
			tsd.from_time,
			tsd.to_time,
			tsd.hours,
			tsd.activity_type,
			tsd.task,
			tsd.project,
			ts.status,
		)
		.where(ts.docstatus == 1)
	)

	if filters.get("from_date"):
		query = query.where(tsd.from_time >= get_combine_datetime(filters.get("from_date"), "00:00:00"))

	if filters.get("to_date"):
		# upper bound is the end of to_date, i.e. midnight of the next day
		# (matches the original `timestamp(to_date, '24:00:00')`)
		end_of_to_date = get_combine_datetime(add_days(getdate(filters.get("to_date")), 1), "00:00:00")
		query = query.where(tsd.to_time <= end_of_to_date)

	return query.orderby(ts.name).run(as_list=True)

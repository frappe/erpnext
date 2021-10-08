# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.desk.reportview import build_match_conditions


def execute(filters=None):
	if not filters:
		filters = {}
	elif filters.get("from_date") or filters.get("to_date"):
		filters["from_time"] = "00:00:00"
		filters["to_time"] = "24:00:00"

	columns = get_column()
	conditions = get_conditions(filters)
	data = get_data(conditions, filters)

	return columns, data

def get_column():
	return [_("Timesheet") + ":Link/Timesheet:120", _("Employee") + "::150", _("Employee Name") + "::150",
		_("From Datetime") + "::140", _("To Datetime") + "::140", _("Hours") + "::70",
		_("Activity Type") + "::120", _("Task") + ":Link/Task:150",
		_("Project") + ":Link/Project:120", _("Status") + "::70"]

def get_data(conditions, filters):
	time_sheet = frappe.db.sql(""" select `tabTimesheet`.name, `tabTimesheet`.employee, `tabTimesheet`.employee_name,
		`tabTimesheet Detail`.from_time, `tabTimesheet Detail`.to_time, `tabTimesheet Detail`.hours,
		`tabTimesheet Detail`.activity_type, `tabTimesheet Detail`.task, `tabTimesheet Detail`.project,
		`tabTimesheet`.status from `tabTimesheet Detail`, `tabTimesheet` where
		`tabTimesheet Detail`.parent = `tabTimesheet`.name and %s order by `tabTimesheet`.name"""%(conditions), filters, as_list=1)

	return time_sheet

def get_conditions(filters):
	conditions = "`tabTimesheet`.docstatus = 1"
	if filters.get("from_date"):
		conditions += " and `tabTimesheet Detail`.from_time >= timestamp(%(from_date)s, %(from_time)s)"
	if filters.get("to_date"):
		conditions += " and `tabTimesheet Detail`.to_time <= timestamp(%(to_date)s, %(to_time)s)"

	match_conditions = build_match_conditions("Timesheet")
	if match_conditions:
		conditions += " and %s" % match_conditions

	return conditions

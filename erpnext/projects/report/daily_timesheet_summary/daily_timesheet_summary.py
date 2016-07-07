# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters:
		filters = {}
	elif filters.get("from_date") or filters.get("to_date"):
		filters["from_time"] = "00:00:00"
		filters["to_time"] = "24:00:00"

	columns = [_("Timesheet") + ":Link/Timesheet:120", _("Employee") + "::150", _("From Datetime") + "::140",
		_("To Datetime") + "::140", _("Hours") + "::70", _("Activity Type") + "::120", _("Task") + ":Link/Task:150",
		_("Project") + ":Link/Project:120", _("Status") + "::70"]
		
	conditions = "ts.docstatus = 1"
	if filters.get("from_date"):
		conditions += " and tsd.from_time >= timestamp(%(from_date)s, %(from_time)s)"
	if filters.get("to_date"):
		conditions += " and tsd.to_time <= timestamp(%(to_date)s, %(to_time)s)"
	
	data = get_data(conditions, filters)

	return columns, data

def get_data(conditions, filters):
	time_sheet = frappe.db.sql(""" select ts.name, ts.employee, tsd.from_time, tsd.to_time, tsd.hours,
		tsd.activity_type, tsd.task, tsd.project, ts.status from `tabTimesheet Detail` tsd, 
		`tabTimesheet` ts where ts.name = tsd.parent and %s order by ts.name"""%(conditions), filters, as_list=1)

	return time_sheet

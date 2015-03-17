# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
	if not filters:
		filters = {}
	elif filters.get("from_date") or filters.get("to_date"):
		filters["from_time"] = "00:00:00"
		filters["to_time"] = "24:00:00"

	columns = [_("Time Log") + ":Link/Time Log:120", _("Employee") + "::150", _("From Datetime") + "::140",
		_("To Datetime") + "::140", _("Hours") + "::70", _("Activity Type") + "::120", _("Task") + ":Link/Task:150",
		_("Task Subject") + "::180", _("Project") + ":Link/Project:120", _("Status") + "::70"]

	user_map = get_user_map()
	task_map = get_task_map()

	conditions = build_conditions(filters)
	time_logs = frappe.db.sql("""select * from `tabTime Log`
		where docstatus < 2 %s order by owner asc""" % (conditions, ), filters, as_dict=1)

	if time_logs:
		users = [time_logs[0].owner]

	data = []
	total_hours = total_employee_hours = count = 0
	for tl in time_logs:
		if tl.owner not in users:
			users.append(tl.owner)
			data.append(["", "", "", "Total", total_employee_hours, "", "", "", "", ""])
			total_employee_hours = 0

		data.append([tl.name, user_map[tl.owner], tl.from_time, tl.to_time, tl.hours,
				tl.activity_type, tl.task, task_map.get(tl.task), tl.project, tl.status])

		count += 1
		total_hours += flt(tl.hours)
		total_employee_hours += flt(tl.hours)

		if count == len(time_logs):
			data.append(["", "", "", "Total Hours", total_employee_hours, "", "", "", "", ""])

	if total_hours:
		data.append(["", "", "", "Grand Total", total_hours, "", "", "", "", ""])

	return columns, data

def get_user_map():
	users = frappe.db.sql("""select name,
		concat(first_name, if(last_name, (' ' + last_name), '')) as fullname
		from tabUser""", as_dict=1)
	user_map = {}
	for p in users:
		user_map.setdefault(p.name, []).append(p.fullname)

	return user_map

def get_task_map():
	tasks = frappe.db.sql("""select name, subject from tabTask""", as_dict=1)
	task_map = {}
	for t in tasks:
		task_map.setdefault(t.name, []).append(t.subject)

	return task_map

def build_conditions(filters):
	conditions = ""
	if filters.get("from_date"):
		conditions += " and from_time >= timestamp(%(from_date)s, %(from_time)s)"
	if filters.get("to_date"):
		conditions += " and to_time <= timestamp(%(to_date)s, %(to_time)s)"

	from frappe.desk.reportview import build_match_conditions
	match_conditions = build_match_conditions("Time Log")
	if match_conditions:
		conditions += " and %s" % match_conditions

	return conditions

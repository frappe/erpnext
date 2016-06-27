# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt,cint

def execute(filters=None):
	simplified_time_log = cint(frappe.db.get_value("Project Settings", None, "simplified_time_log"))
	if not filters:
		filters = {}
	elif filters.get("from_date") or filters.get("to_date"):
		filters["from_time"] = "00:00:00"
		if simplified_time_log:
			filters["to_time"] = "23:59:59"
		else:
			filters["to_time"] = "24:00:00"
	
	
	columns = [_("Time Log") + ":Link/Time Log:100",
		_("Employee") + "::150"]

	if simplified_time_log:
		columns.append(_("Date") + "::100")
	else:
		columns.append(_("From Datetime") + "::140")
		columns.append(_("To Datetime") + "::140")
	
	columns_part = [
		_("Hours") + "::60",
		_("Activity Type") + "::180",
		_("Project") + ":Link/Project:180",
		_("Task") + ":Link/Task:100",
		_("Task Subject") + "::180",
		_("Status") + "::70"]
	
	columns.extend(columns_part)
	
	user_map = get_user_map()
	employee_map = get_employee_map()
	task_map = get_task_map()
	
	conditions = build_conditions(filters)
	if simplified_time_log:
		time_logs = frappe.db.sql("""select * from `tabTime Log`
			where docstatus < 2 %s order by employee_name asc, date_worked asc""" % (conditions, ), filters, as_dict=1)
	else:
		time_logs = frappe.db.sql("""select * from `tabTime Log`
			where docstatus < 2 %s order by employee_name asc, from_time asc, to_time asc""" % (conditions, ), filters, as_dict=1)

	if time_logs:
		users = [time_logs[0].employee]

	data = []
	total_hours = total_employee_hours = count = 0
	for tl in time_logs:
		if tl.employee:
			employee=employee_map[tl.employee]
		else:
			employee=user_map[tl.owner]	
		if tl.owner not in users:
			users.append(tl.owner)
			data.append(["", "", "", "Total", total_employee_hours, "", "", "", "", ""])
			total_employee_hours = 0

		data.append([tl.name, employee, tl.from_time, tl.to_time, tl.hours,
				tl.activity_type, tl.task, task_map.get(tl.task), tl.project, tl.status])

		if tl.employee not in users:
			users.append(tl.employee)
			if simplified_time_log:
				data.append(["", "", "Total", total_employee_hours, "", "", "", "", ""])
			else:
				data.append(["", "", "", "Total", total_employee_hours,  "", "", "", "", ""])
			
			total_employee_hours = 0
		
		if simplified_time_log:
			data.append([tl.name, tl.employee_name, tl.date_worked, tl.hours,
				tl.activity_type, tl.project, tl.task, task_map.get(tl.task), tl.status])

		else:
			data.append([tl.name, tl.employee_name, tl.from_time, tl.to_time, tl.hours,
				tl.activity_type, tl.project, tl.task, task_map.get(tl.task), tl.status])
		
		count += 1
		total_hours += flt(tl.hours)
		total_employee_hours += flt(tl.hours)

		if count == len(time_logs):
			if simplified_time_log:
				data.append(["", "", "Total Hours", total_employee_hours, "", "", "", "", ""])
			else:
				data.append(["", "", "", "Total Hours", total_employee_hours, "", "", "", "", ""])

	if total_hours:
		if simplified_time_log:
			data.append(["", "", "Grand Total", total_hours, "", "", "", "", ""])
		else:
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
	
def get_employee_map():
	employees = frappe.db.sql("""select name,
		employee_name as fullname
		from tabEmployee""", as_dict=1)
	employee_map = {}
	for p in employees:
		employee_map.setdefault(p.name, []).append(p.fullname)

	return employee_map	

def get_task_map():
	tasks = frappe.db.sql("""select name, subject from tabTask""", as_dict=1)
	task_map = {}
	for t in tasks:
		task_map.setdefault(t.name, []).append(t.subject)

	return task_map

def build_conditions(filters):
	simplified_time_log = cint(frappe.db.get_value("Project Settings", None, "simplified_time_log"))
	
	conditions = ""
	if filters.get("from_date"):
		if simplified_time_log:
			conditions += " and date_worked >= timestamp(%(from_date)s, %(from_time)s)"
		else:
			conditions += " and from_time >= timestamp(%(from_date)s, %(from_time)s)"
	if filters.get("to_date"):
		if simplified_time_log:
			conditions += " and date_worked <= timestamp(%(to_date)s, %(to_time)s)"
		else:	
			conditions += " and to_time <= timestamp(%(to_date)s, %(to_time)s)"
	
	if filters.get("employee"):
		conditions += " and employee = %(employee)s"

	from frappe.desk.reportview import build_match_conditions
	match_conditions = build_match_conditions("Time Log")
	if match_conditions:
		conditions += " and %s" % match_conditions

	return conditions

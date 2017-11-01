# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):

	if not filters: filters = {}

	columns = get_columns()
	data = get_employees(filters)

	return columns, data

def get_columns():
	return [("Employee") + ":Link/Employee:120", ("Name") + ":Data:200",("Designation") + ":Link/Designation:120",
			("Attendance")+":Time"
		,("departure")+":Time"
		,("working_hours")+":Time"
		, ("early_entry") + ":Time"
		, ("delay") + ":Time"
		, ("early_exit") + ":Time"
		, ("allow_to") + ":Time"
		, ("over_time") + ":Time"
		, ("total") + ":Time"
		, ("actual") + ":Time"
		,("Date")+":Time"
	]

def get_employees(filters):
	conditions = get_conditions(filters)

	return frappe.db.sql("""select name, employee_name,designation,attendance,departure,working_hours,early_entry,
	delay,early_exit,allow_to,over_time,total,actual,attendance_date
	 from tabAttendance where employee_status = 'Active' %s""" % conditions, as_list=1)


def get_conditions(filters):
	conditions = ""

	if filters.get("employee"): conditions += " and employee = '%s'" % \
		filters["employee"].replace("'", "\\'")
	if filters.get("company"): conditions += " and company = '%s'" % \
		filters["company"].replace("'", "\\'")

	if filters.get("from_date"): conditions += " and attendance_date >= '%(from_date)s'" % {'from_date':filters["from_date"].replace("'", "\\'")}  
	if filters.get("to_date"): conditions += " and attendance_date <= '%(to_date)s'" % {'to_date':filters["to_date"]}






	return conditions



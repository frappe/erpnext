# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()
	data = get_employees(filters)

	return columns, data

def get_columns():
	return [
		"Employee:Link/Employee:120", "Name:Data:200", "Date of Birth:Date:100",
		"Branch:Link/Branch:120", "Department:Link/Department:120",
		"Designation:Link/Designation:120", "Gender::60", "Company:Link/Company:120"
	]

def get_employees(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select name, employee_name, date_of_birth,
	branch, department, designation,
	gender, company from tabEmployee where status = 'Active' %s""" % conditions, as_list=1)

def get_conditions(filters):
	conditions = ""
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
			"Dec"].index(filters["month"]) + 1
		conditions += " and month(date_of_birth) = '%s'" % month

	if filters.get("company"): conditions += " and company = '%s'" % \
		filters["company"].replace("'", "\\'")

	return conditions

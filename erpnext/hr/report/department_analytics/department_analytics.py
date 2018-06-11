# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns = get_columns()
	employees = get_employees(filters)
	departments_result = get_department(filters)
	departments = []
	if departments_result:
		for department in departments_result:
			departments.append(department)
	chart = get_chart_data(departments,employees)
	return columns, employees, None, chart

def get_columns():
	return [
		_("Employee") + ":Link/Employee:120", _("Name") + ":Data:200", _("Date of Birth")+ ":Date:100",
		_("Branch") + ":Link/Branch:120", _("Department") + ":Link/Department:120",
		_("Designation") + ":Link/Designation:120", _("Gender") + "::60", _("Company") + ":Link/Company:120"
	]

def get_conditions(filters):
	conditions = ""
	if filters.get("department"): conditions += " and department = '%s'" % \
		filters["department"].replace("'", "\\'")
	return conditions

def get_employees(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select name, employee_name, date_of_birth,
	branch, department, designation,
	gender, company from `tabEmployee` where status = 'Active' %s""" % conditions, as_list=1)

def get_department(filters):
	return frappe.db.sql("""select name from `tabDepartment`""" , as_list=1)
	
def get_chart_data(departments,employees):
	if not departments:
		departments = []
	datasets = []
	for department in departments:
		if department:
			total_employee = frappe.db.sql("""select count(*) from \
				`tabEmployee` where \
				department = %s""" ,(department[0]), as_list=1)
			datasets.append(total_employee[0][0])
	chart = {
		"data": {
			'labels': departments,
			'datasets': [{'name': 'Employees','values': datasets}]
		}
	}
	chart["type"] = "bar"
	return chart


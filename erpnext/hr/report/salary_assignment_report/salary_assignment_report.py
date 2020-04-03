# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns = [
		_("Company") + "::240", _("Employee") + "::240", _("Department") + "::170", _("Salary Slip") + "::160",
		_("Salary Allocation") + "::170", _("Total") + ":Currency:120"
	]

	conditions = return_filters(filters)
	data = []
	total = 0
	salary_component = frappe.get_all("Assignment Salary Component", ["name", "payroll_entry", "salary_component"], filters = conditions)
	for item in salary_component:
		filters_item = get_item(filters, item.name)
		employee_detail = frappe.get_all("Employee Detail Salary Component", ["employee_name", "moneda"], filters = filters_item)
		for item_employee in employee_detail:
			employee = item_employee.employee_name
			filters_employee = get_employee(filters, employee)
			employee = frappe.get_all("Employee", ["department", "company"], filters = filters_employee)
			for verificate in employee:
				row = [verificate.company, item_employee.employee_name, verificate.department, item.payroll_entry, item.salary_component, item_employee.moneda]
				data.append(row)
	
	return columns, data

def return_filters(filters):
	conditions = ''

	conditions += "{"
	if filters.get("payroll_entry"): conditions += '"payroll_entry": "{}"'.format(filters.get("payroll_entry"))
	if filters.get("salary_component"): conditions += ', "salary_component": "{}"'.format(filters.get("salary_component"))
	conditions += '}'

	return conditions

def get_item(filters, item):
	conditions = ''

	conditions += '{'
	conditions += '"parent": "{}"'.format(item)
	if filters.get("employee"): conditions += ', "employee": "{}"'.format(filters.get("employee"))
	conditions += "}"

	return conditions

def get_employee(filters, employee):
	conditions = ''

	conditions += "{"
	conditions += '"employee_name": "{}"'.format(employee)
	if filters.get("company"): conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("department"): conditions += ', "department": "{}"'.format(filters.get("department"))
	conditions += '}'

	return conditions

# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_columns(filters):
	columns = [
		{
			"label": _("Employee"),
			"options": "Employee",
			"fieldname": "employee",
			"fieldtype": "Link",
			"width": 200
		},
		{
			"label": _("Employee Name"),
			"options": "Employee",
			"fieldname": "employee_name",
			"fieldtype": "Link",
			"width": 160
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Data",
			"width": 140
		}
	]

	return columns

def get_conditions(filters):
	conditions = [""]

	if filters.get("department"):
		conditions.append("sal.department = '%s' " % (filters["department"]) )

	if filters.get("branch"):
		conditions.append("sal.branch = '%s' " % (filters["branch"]) )

	if filters.get("company"):
		conditions.append("sal.company = '%s' " % (filters["company"]) )

	if filters.get("period"):
		conditions.append("month(sal.start_date) = '%s' " % (filters["period"]))

	return " and ".join(conditions)

def get_data(filters):

	data = []

	component_type_dict = frappe._dict(frappe.db.sql(""" select name, component_type from `tabSalary Component`
		where component_type = 'Professional Tax' """))

	conditions = get_conditions(filters)

	entry = frappe.db.sql(""" select sal.employee, sal.employee_name, ded.salary_component, ded.amount 
		from `tabSalary Slip` sal, `tabSalary Detail` ded
		where sal.name = ded.parent
		and ded.parentfield = 'deductions'
		and ded.parenttype = 'Salary Slip'
		and sal.docstatus = 1 %s
		and ded.salary_component in (%s)
	""" % (conditions , ", ".join(['%s']*len(component_type_dict))), tuple(component_type_dict.keys()), as_dict=1)

	for d in entry:
	
		employee = {
			"employee": d.employee,
			"employee_name": d.employee_name,
			"amount": d.amount
		}

		data.append(employee)

	return data
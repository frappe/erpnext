# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.regional.report.provident_fund_deductions.provident_fund_deductions import get_conditions

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
			"label": _("PAN Number"),
			"fieldname": "pan_number",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("Income Tax Amount"),
			"fieldname": "it_amount",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Gross Pay"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"width": 140
		}
	]

	return columns

def get_data(filters):
	data = []

	employee_pan_dict = frappe._dict(frappe.db.sql(""" select employee, pan_number from `tabEmployee`"""))

	component_type_dict = frappe._dict(frappe.db.sql(""" select name, component_type from `tabSalary Component`
		where component_type = 'Income Tax' """))

	conditions = get_conditions(filters)

	entry = frappe.db.sql(""" select sal.employee, sal.employee_name, ded.salary_component, ded.amount,sal.gross_pay
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
			"pan_number": employee_pan_dict.get(d.employee),
			"it_amount": d.amount,
			"gross_pay": d.gross_pay
		}

		data.append(employee)

	return data


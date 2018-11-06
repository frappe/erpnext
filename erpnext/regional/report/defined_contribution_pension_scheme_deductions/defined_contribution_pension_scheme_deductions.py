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
			"label": _("Employee Number"),
			"options": "Employee",
			"fieldname": "employee_number",
			"fieldtype": "Link",
			"width": 200
		},
		{
			"label": _("Employee Name"),
			"options": "Employee",
			"fieldname": "employee_name",
			"width": 160
		},
		{
			"label": _("DCPS Account Number"),
			"fieldname": "dcps_account",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("DCPS Amount"),
			"fieldname": "dcps_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140
		},
		{
			"label": _("DCPS Received"),
			"fieldname": "dcps_received",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140
		},
		{
			"label": _("Total"),
			"fieldname": "total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140
		}
	]

	return columns

def get_data(filters):

	data = []

	employee_account_dict = frappe._dict(frappe.db.sql(""" select employee_number, DCPS_account from `tabEmployee`"""))
 
	component_type_dict = frappe._dict(frappe.db.sql(""" select name, component_type from `tabSalary Component`
		where component_type in ('Defined Contribution Pension Scheme')"""))

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
		total = 0
		employee = {
			"employee_number": d.employee,
			"employee_name": d.employee_name,
			"dcps_account": employee_account_dict.get(d.employee),
			"dcps_amount": d.amount
		}

		total += d.amount
		employee["total"] = total
		data.append(employee)
		
	return data


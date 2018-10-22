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
			"label": _("PF Account"),
			"fieldname": "pf_account",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("PF Amount"),
			"fieldname": "pf_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140
		},
		{
			"label": _("Additional PF"),
			"fieldname": "additional_pf",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140
		},
		{
			"label": _("PF Loan"),
			"fieldname": "pf_loan",
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

	employee_account_dict = frappe._dict(frappe.db.sql(""" select name, provident_fund_account from `tabEmployee`"""))

	component_type_dict = frappe._dict(frappe.db.sql(""" select name, component_type from `tabSalary Component`
		where component_type in ('Provident Fund', 'Additional Provident Fund', 'Provident Fund Loan')"""))

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
			"employee": d.employee,
			"employee_name": d.employee_name,
			"pf_account": employee_account_dict.get(d.employee)
		}

		if component_type_dict.get(d.salary_component) == 'Provident Fund':
			employee["pf_amount"] = d.amount
			total += d.amount
		
		if component_type_dict.get(d.salary_component) == 'Additional Provident Fund':
			employee["additional_pf"] = d.amount
			total += d.amount

		if component_type_dict.get(d.salary_component) == 'Provident Fund Loan':
			employee["pf_loan"] = d.amount
			total += d.amount
		
		employee["total"] = total

		data.append(employee)

	return data

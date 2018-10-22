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
			"label": _("Branch"),
			"options": "Branch",
			"fieldname": "branch",
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
			"label": _("Employee"),
			"options":"Employee",
			"fieldname": "employee",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Gross Pay"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140
		},
		{
			"label": _("Account No"),
			"fieldname": "account_no",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("IFSC"),
			"fieldname": "ifsc",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("MICR"),
			"fieldname": "micr",
			"fieldtype": "Data",
			"width": 140
		}
	]

	return columns

def get_conditions(filters):
	conditions = [""]

	if filters.get("department"):
		conditions.append("department = '%s' " % (filters["department"]) )

	if filters.get("branch"):
		conditions.append("branch = '%s' " % (filters["branch"]) )

	if filters.get("company"):
		conditions.append("company = '%s' " % (filters["company"]) )

	if filters.get("period"):
		conditions.append("month(start_date) = '%s' " % (filters["period"]))

	return " and ".join(conditions)

def get_data(filters):

	data = []

	employee_details = frappe.get_list("Employee", fields = ["employee", "branch", "bank_ac_no", "ifsc_code", "micr", "salary_mode"])

	employee_data_dict = {}

	for d in employee_details:
		employee_data_dict.setdefault(
			d.employee,{
				"bank_ac_no" : d.bank_ac_no,
				"ifsc_code" : d.ifsc_code,
				"micr" : d.micr,
				"branch" : d.branch,
				"salary_mode" : d.salary_mode
			}
		)

	conditions = get_conditions(filters)

	entry = frappe.db.sql(""" select employee, employee_name, gross_pay 
		from `tabSalary Slip` 
		where docstatus = 1 %s """
		%(conditions), as_dict =1)

	for d in entry:
		
		employee = {
			"branch" : employee_data_dict.get(d.employee).get("branch"),
			"employee_name" : d.employee_name,
			"employee" : d.employee,
			"gross_pay" : d.gross_pay,
		}

		if employee_data_dict.get(d.employee).get("salary_mode") == "Bank":
			employee["account_no"] = employee_data_dict.get(d.employee).get("bank_ac_no")
			employee["ifsc"] = employee_data_dict.get(d.employee).get("ifsc_code")
			employee["micr"] = employee_data_dict.get(d.employee).get("micr")
		else:
			employee["account_no"] = employee_data_dict.get(d.employee).get("salary_mode")

		if filters.get("type") and employee_data_dict.get(d.employee).get("salary_mode") == filters.get("type"):
			data.append(employee)
		elif not filters.get("type"):
			data.append(employee)

	return data

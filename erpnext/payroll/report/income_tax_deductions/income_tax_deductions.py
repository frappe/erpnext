# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _

import erpnext


def execute(filters=None):
	data = get_data(filters)
	columns = get_columns(filters) if len(data) else []

	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Employee"),
			"options": "Employee",
			"fieldname": "employee",
			"fieldtype": "Link",
			"width": 200,
		},
		{
			"label": _("Employee Name"),
			"options": "Employee",
			"fieldname": "employee_name",
			"fieldtype": "Link",
			"width": 160,
		},
	]

	if erpnext.get_region() == "India":
		columns.append(
			{"label": _("PAN Number"), "fieldname": "pan_number", "fieldtype": "Data", "width": 140}
		)

	columns += [
		{"label": _("Income Tax Component"), "fieldname": "it_comp", "fieldtype": "Data", "width": 170},
		{
			"label": _("Income Tax Amount"),
			"fieldname": "it_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"label": _("Gross Pay"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 140},
	]

	return columns


def get_conditions(filters):
	conditions = [""]

	if filters.get("department"):
		conditions.append("sal.department = '%s' " % (filters["department"]))

	if filters.get("branch"):
		conditions.append("sal.branch = '%s' " % (filters["branch"]))

	if filters.get("company"):
		conditions.append("sal.company = '%s' " % (filters["company"]))

	if filters.get("month"):
		conditions.append("month(sal.start_date) = '%s' " % (filters["month"]))

	if filters.get("year"):
		conditions.append("year(start_date) = '%s' " % (filters["year"]))

	return " and ".join(conditions)


def get_data(filters):

	data = []

	if erpnext.get_region() == "India":
		employee_pan_dict = frappe._dict(
			frappe.db.sql(""" select employee, pan_number from `tabEmployee`""")
		)

	component_types = frappe.db.sql(
		""" select name from `tabSalary Component`
		where is_income_tax_component = 1 """
	)

	component_types = [comp_type[0] for comp_type in component_types]

	if not len(component_types):
		return []

	conditions = get_conditions(filters)

	entry = frappe.db.sql(
		""" select sal.employee, sal.employee_name, sal.posting_date, ded.salary_component, ded.amount,sal.gross_pay
		from `tabSalary Slip` sal, `tabSalary Detail` ded
		where sal.name = ded.parent
		and ded.parentfield = 'deductions'
		and ded.parenttype = 'Salary Slip'
		and sal.docstatus = 1 %s
		and ded.salary_component in (%s)
	"""
		% (conditions, ", ".join(["%s"] * len(component_types))),
		tuple(component_types),
		as_dict=1,
	)

	for d in entry:

		employee = {
			"employee": d.employee,
			"employee_name": d.employee_name,
			"it_comp": d.salary_component,
			"posting_date": d.posting_date,
			# "pan_number": employee_pan_dict.get(d.employee),
			"it_amount": d.amount,
			"gross_pay": d.gross_pay,
		}

		if erpnext.get_region() == "India":
			employee["pan_number"] = employee_pan_dict.get(d.employee)

		data.append(employee)

	return data

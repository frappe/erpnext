# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	data = get_data(filters)
	columns = get_columns(filters) if len(data) else []

	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 200,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"width": 160,
		},
		{"label": _("PF Account"), "fieldname": "pf_account", "fieldtype": "Data", "width": 140},
		{"label": _("PF Amount"), "fieldname": "pf_amount", "fieldtype": "Currency", "width": 140},
		{
			"label": _("Additional PF"),
			"fieldname": "additional_pf",
			"fieldtype": "Currency",
			"width": 140,
		},
		{"label": _("PF Loan"), "fieldname": "pf_loan", "fieldtype": "Currency", "width": 140},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 140},
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

	if filters.get("mode_of_payment"):
		conditions.append("sal.mode_of_payment = '%s' " % (filters["mode_of_payment"]))

	return " and ".join(conditions)


def prepare_data(entry, component_type_dict):
	data_list = {}

	employee_account_dict = frappe._dict(
		frappe.db.sql(""" select name, provident_fund_account from `tabEmployee`""")
	)

	for d in entry:

		component_type = component_type_dict.get(d.salary_component)

		if data_list.get(d.name):
			data_list[d.name][component_type] = d.amount
		else:
			data_list.setdefault(
				d.name,
				{
					"employee": d.employee,
					"employee_name": d.employee_name,
					"pf_account": employee_account_dict.get(d.employee),
					component_type: d.amount,
				},
			)

	return data_list


def get_data(filters):
	data = []

	conditions = get_conditions(filters)

	salary_slips = frappe.db.sql(
		""" select sal.name from `tabSalary Slip` sal
		where docstatus = 1 %s
		"""
		% (conditions),
		as_dict=1,
	)

	component_type_dict = frappe._dict(
		frappe.db.sql(
			""" select name, component_type from `tabSalary Component`
		where component_type in ('Provident Fund', 'Additional Provident Fund', 'Provident Fund Loan')"""
		)
	)

	if not len(component_type_dict):
		return []

	entry = frappe.db.sql(
		""" select sal.name, sal.employee, sal.employee_name, ded.salary_component, ded.amount
		from `tabSalary Slip` sal, `tabSalary Detail` ded
		where sal.name = ded.parent
		and ded.parentfield = 'deductions'
		and ded.parenttype = 'Salary Slip'
		and sal.docstatus = 1 %s
		and ded.salary_component in (%s)
	"""
		% (conditions, ", ".join(["%s"] * len(component_type_dict))),
		tuple(component_type_dict.keys()),
		as_dict=1,
	)

	data_list = prepare_data(entry, component_type_dict)

	for d in salary_slips:
		total = 0
		if data_list.get(d.name):
			employee = {
				"employee": data_list.get(d.name).get("employee"),
				"employee_name": data_list.get(d.name).get("employee_name"),
				"pf_account": data_list.get(d.name).get("pf_account"),
			}

			if data_list.get(d.name).get("Provident Fund"):
				employee["pf_amount"] = data_list.get(d.name).get("Provident Fund")
				total += data_list.get(d.name).get("Provident Fund")

			if data_list.get(d.name).get("Additional Provident Fund"):
				employee["additional_pf"] = data_list.get(d.name).get("Additional Provident Fund")
				total += data_list.get(d.name).get("Additional Provident Fund")

			if data_list.get(d.name).get("Provident Fund Loan"):
				employee["pf_loan"] = data_list.get(d.name).get("Provident Fund Loan")
				total += data_list.get(d.name).get("Provident Fund Loan")

			employee["total"] = total

			data.append(employee)

	return data


@frappe.whitelist()
def get_years():
	year_list = frappe.db.sql_list(
		"""select distinct YEAR(end_date) from `tabSalary Slip` ORDER BY YEAR(end_date) DESC"""
	)
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)

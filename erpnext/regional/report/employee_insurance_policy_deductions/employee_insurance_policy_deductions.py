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
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("Policy Number"),
			"fieldname": "policy_number",
			"fieldtype": "Data",
			"options": "Data",
			"width": 140
		},
		{
			"label": _("Premium"),
			"fieldname": "premium",
			"fieldtype": "Data",
			"options": "Data",
			"width": 140
		},
		{
			"label": _("Total"),
			"fieldname": "total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140
		},
		{
			"label": _("Salary Deducted"),
			"fieldname": "salary_deducted",
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
 
	component_type_dict = frappe._dict(frappe.db.sql(""" select name, component_type from `tabSalary Component`
		where component_type in ('Life Insurance')"""))

	employee_insurance_record = frappe.get_all("Employee Insurance", 
									fields=["employee","policy_no","monthly_premium","premium_start_date","premium_end_date"],
									filters={
										"deduct_from_salary" : True
									})
	conditions = get_conditions(filters)

	entry = frappe.db.sql(""" select sal.employee, sal.employee_name, sal.department, sal.start_date, sal.end_date, ded.salary_component, ded.amount 
			from `tabSalary Slip` sal, `tabSalary Detail` ded
			where sal.name = ded.parent
			and ded.parentfield = 'deductions'
			and ded.parenttype = 'Salary Slip'
			and sal.docstatus = 1 %s
			and ded.salary_component in (%s)
		""" % (conditions , ", ".join(['%s']*len(component_type_dict))), tuple(component_type_dict.keys()), as_dict=1)

	grouped_records={}

	for record in employee_insurance_record:
		grouped_records.setdefault(record.employee, []).append(record)


	for d in entry:
		total = 0
		policy_number_list=[]
		employee = {
			"employee_number": d.employee,
			"employee_name": d.employee_name,
			"department": d.department
		}
		employee_record = grouped_records.get(d.employee,[])
		policy_number_list = []
		monthly_premium_list = []
		for e in employee_record:
			if ((e['premium_end_date'] - d.start_date).days >= 0 and (d.end_date - e['premium_start_date']).days >= 0):
				policy_number_list.append(str(e['policy_no']))		
				monthly_premium_list.append(str(e['monthly_premium']))

		employee["policy_number"] = ", ".join(policy_number_list)
		employee["premium"] =  ", ".join(monthly_premium_list)
		total += d.amount
		employee["total"] = total
		employee["salary_deducted"] = total
		data.append(employee)
	return data

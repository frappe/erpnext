# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns, salary_components_Earning, salary_components_deduction = get_columns()
	data = []

	conditions = get_conditions(filters)

	confidential_list = []

	roles_arr = []

	confidential_payroll = frappe.get_all("Confidential Payroll Employee", ["*"])

	if len(confidential_payroll) > 0:

		employees = frappe.get_all("Confidential Payroll Detail", ["*"], filters = {"parent": confidential_payroll[0].name})

		for employee in employees:
			confidential_list.append(employee.employee)
		
		user = frappe.session.user

		users = frappe.get_all("User", ["*"], filters = {"name": user})

		roles = frappe.get_all("Has Role", ["*"], filters = {"parent": users[0].name})

		for role in roles:
			roles_arr.append(role.role)	

	salary_slips = frappe.get_all("Salary Slip", ["name", "employee", "gross_pay", "total_deduction", "net_pay", "employee_name", "payment_days", "payroll_entry"], filters = conditions)
	
	for ss in salary_slips:
		Employee = frappe.get_all("Salary Structure Assignment", ["name", "employee","employee_name", "base"], filters = {"employee": ss.employee})

		salary_detail = frappe.get_all("Salary Detail", ["name", "salary_component", "amount"], filters = {"parent":ss.name})

		row = [ss.employee_name, ss.payment_days]

		if len(Employee) > 0:		
			row += [Employee[0].base]
		else:
			row += [0]

		for sc in salary_components_Earning:
			salarydetail = frappe.get_all("Salary Detail", ["name", "salary_component", "amount"], filters = {"salary_component":sc.name})
			if len(salarydetail) > 0:
				value_component = 0
				for sdd in salary_detail:
					if sc.name == sdd.salary_component:
						value_component = sdd.amount

						assigments = frappe.get_all("Assignment Salary Component", ["name"], filters = {"payroll_entry": ss.payroll_entry, "salary_component": sc.name, "docstatus": 0})

						for assigment in assigments:
							employees = frappe.get_all("Employee Detail Salary Component", ["*"], filters = {"parent": assigment.name, "employee": ss.employee})

							for employee in employees:
								value_component += employee.moneda		

						#Confidentials
						assigments = frappe.get_all("Assignment Salary Component Confidential", ["name"], filters = {"payroll_entry": ss.payroll_entry, "salary_component": sc.name, "docstatus": 0})

						for assigment in assigments:
							employees = frappe.get_all("Employee Detail Salary Component Confidential", ["*"], filters = {"parent": assigment.name, "employee": ss.employee})

							for employee in employees:
								value_component += employee.moneda						
					else:
						assigments = frappe.get_all("Assignment Salary Component", ["name"], filters = {"payroll_entry": ss.payroll_entry, "salary_component": sc.name, "docstatus": 0})

						for assigment in assigments:
							employees = frappe.get_all("Employee Detail Salary Component", ["*"], filters = {"parent": assigment.name, "employee": ss.employee})

							for employee in employees:
								value_component += employee.moneda
						
						#Confidentials
						assigments = frappe.get_all("Assignment Salary Component Confidential", ["name"], filters = {"payroll_entry": ss.payroll_entry, "salary_component": sc.name, "docstatus": 0})

						for assigment in assigments:
							employees = frappe.get_all("Employee Detail Salary Component Confidential", ["*"], filters = {"parent": assigment.name, "employee": ss.employee})

							for employee in employees:
								value_component += employee.moneda	

					if value_component > 0:
						break
					
				row += [value_component]
			# else:
			# 	row += [0]

		incomes = 0

		income_list = frappe.get_all("Salary Detail", ["*"], filters = {"parent": ss.name})

		for inc in income_list:
			component = frappe.get_doc("Salary Component", inc.salary_component)

			if component.type == "Earning" and component.name != "Base":
				incomes += inc.amount

		# row += [incomes]

		row += [ss.gross_pay]

		net_pay = ss.net_pay
		total_deduction = ss.total_deduction

		for coldata in salary_components_deduction:			
			salarydetail = frappe.get_all("Salary Detail", ["name", "salary_component", "amount"], filters = {"salary_component":coldata.name})
			if len(salarydetail) > 0:
				value_component = 0
				for sdd in salary_detail:
					if coldata.name == sdd.salary_component:
						value_component = sdd.amount

						assigments = frappe.get_all("Assignment Salary Component", ["name"], filters = {"payroll_entry": ss.payroll_entry, "salary_component": coldata.name, "docstatus": 0})

						for assigment in assigments:
							employees = frappe.get_all("Employee Detail Salary Component", ["*"], filters = {"parent": assigment.name, "employee": ss.employee})

							for employee in employees:
								value_component += employee.moneda
								if assigment.type == "Earning":
									net_pay += employee.moneda
								else:
									net_pay -= employee.moneda	
									total_deduction += employee.moneda

						#Confidentials
						assigments = frappe.get_all("Assignment Salary Component Confidential", ["name"], filters = {"payroll_entry": ss.payroll_entry, "salary_component": coldata.name, "docstatus": 0})

						for assigment in assigments:
							employees = frappe.get_all("Employee Detail Salary Component Confidential", ["*"], filters = {"parent": assigment.name, "employee": ss.employee})

							for employee in employees:
								value_component += employee.moneda
								if assigment.type == "Earning":
									net_pay += employee.moneda
								else:
									net_pay -= employee.moneda
									total_deduction += employee.moneda
					else:
						assigments = frappe.get_all("Assignment Salary Component", ["name"], filters = {"payroll_entry": ss.payroll_entry, "salary_component": coldata.name, "docstatus": 0})

						for assigment in assigments:
							employees = frappe.get_all("Employee Detail Salary Component", ["*"], filters = {"parent": assigment.name, "employee": ss.employee})

							for employee in employees:
								value_component += employee.moneda
								if assigment.type == "Earning":
									net_pay += employee.moneda
								else:
									net_pay -= employee.moneda
									total_deduction += employee.moneda
						
						#Confidentials
						assigments = frappe.get_all("Assignment Salary Component Confidential", ["name"], filters = {"payroll_entry": ss.payroll_entry, "salary_component": coldata.name, "docstatus": 0})

						for assigment in assigments:
							employees = frappe.get_all("Employee Detail Salary Component Confidential", ["*"], filters = {"parent": assigment.name, "employee": ss.employee})

							for employee in employees:
								value_component += employee.moneda
								if assigment.type == "Earning":
									net_pay += employee.moneda
								else:
									net_pay -= employee.moneda
									total_deduction += employee.moneda
					
					if value_component > 0:
						break
				
				row += [value_component]	
			# else:
			# 	row += [0]	

		row += [total_deduction, net_pay]

		if ss.employee in confidential_list:
			if confidential_payroll[0].rol in roles_arr:
				if filters.get("department"):
					employee_data = frappe.get_doc("Employee", ss.employee)
					if employee_data.department == filters.get("department"):
						data.append(row)
				else:
					data.append(row)
		else:
			if filters.get("department"):
				employee_data = frappe.get_doc("Employee", ss.employee)
				if employee_data.department == filters.get("department"):
					data.append(row)
			else:
				data.append(row)
	
	row = ["ELABORADO POR:"]

	for column in columns:
		row += [""]

	data.append(row)

	row = ["REVISADO POR:"]
	
	for column in columns:
		row += [""]

	data.append(row)

	return columns, data

def get_columns():
	dat = []
	column = [
		_("Employee Name") + "::140", _("Payment Days") + ":Float:120", _("Salary Base") + ":Currency:120",		
	]
	salary_components_Earning = frappe.get_all("Salary Component", ["name"], filters = {"type": "Earning"})

	for sc in salary_components_Earning:
		salarydetail = frappe.get_all("Salary Detail", ["name", "salary_component", "amount"], filters = {"salary_component":sc.name})
		if len(salarydetail) > 0:
			component = str(sc.name)
			column.append(_(component) + ":Currency:120")
	
	# column.append(_("Extra Income") + ":Currency:120")
	column.append(_("Gross Pay") + ":Currency:120")

	salary_components_deduction = frappe.get_all("Salary Component", ["name"], filters = {"type": "Deduction"})

	for sd in salary_components_deduction:
		salarydetail = frappe.get_all("Salary Detail", ["name", "salary_component", "amount"], filters = {"salary_component":sd.name})
		if len(salarydetail) > 0:
			component = str(sd.name)
			column.append(_(component) + ":Currency:120")

	column.append(_("Total Deduction") + ":Currency:120")
	column.append(_("Net Pay") + ":Currency:120")	

	return column, salary_components_Earning, salary_components_deduction

def get_conditions(filters):
	conditions = ''
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	conditions += "{"
	if filters.get("docstatus"):
		conditions += '"docstatus": {0}, '.format(doc_status[filters.get("docstatus")])

	if filters.get("from_date"): conditions += '"start_date": [">=", "{}"], '.format(filters.get("from_date"))
	if filters.get("to_date"): conditions += '"end_date": ["<=", "{}"]'.format(filters.get("to_date"))
	if filters.get("company"): conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("employee"): conditions += ', "employee": "{}"'.format(filters.get("employee"))
	conditions += "}"

	return conditions

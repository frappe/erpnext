# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _,msgprint

def execute(self,filters=None):
	columns = [
		_("Company") + "::240", _("Employee") + "::240", _("Department") + "::170", _("Salary Slip") + "::160",
		_("Salary Allocation") + "::170", _("Total") + ":Currency:120"
	]

	data = []
	total = 0
	if self.salary_component != None:
		salary_component = frappe.get_list("Assignment Salary Component", filters={"payroll_entry": self.payroll_entry, "salary_component": self.salary_component}, fields={"name", "payroll_entry", "salary_component"})
	else:
		salary_component = frappe.get_list("Assignment Salary Component", filters={"payroll_entry": self.payroll_entry}, fields={"name", "payroll_entry", "salary_component"})
	for item in salary_component:
		if self.employee != None:
			employee_detail = frappe.get_all("Employee Detail Salary Component", filters={"parent": item.name, "employee": self.employee}, fields={"employee_name", "moneda"})
		else:
			employee_detail = frappe.get_all("Employee Detail Salary Component", filters={"parent": item.name}, fields={"employee_name", "moneda"})
		for item_employee in employee_detail:
			total += item_employee.moneda
			if self.department != None:
				employee = frappe.get_all("Employee", filters={"employee_name": item_employee.employee_name, "department": self.department}, fields={"department", "company"})
			elif self.company != None:
				employee = frappe.get_all("Employee", filters={"employee_name": item_employee.employee_name, "company": self.company}, fields={"department", "company"})
			elif self.department == None and self.company == None:
				employee = frappe.get_all("Employee", filters={"employee_name": item_employee.employee_name}, fields={"department", "company"})
			for verificate in employee:
				row = [verificate.company, item_employee.employee_name, verificate.department, item.payroll_entry, item.salary_component, item_employee.moneda]
				data.append(row)
	row2 = ["","","","","Total", total]
	data.append(row2)
	
	return columns, data

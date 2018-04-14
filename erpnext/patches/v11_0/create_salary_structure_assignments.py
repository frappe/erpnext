# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("hr", "doctype", "salary_structure_assignment")
	for d in frappe.db.sql("""
		select * from `tabSalary Structure Employee` sse, `tabSalary Structure` ss
		where ss.name = sse.parent""", as_dict=1):

		s = frappe.new_doc("Salary Structure Assignment")
		s.employee = d.employee
		s.employee_name = d.employee_name
		s.salary_structure = d.parent
		s.from_date = d.from_date
		s.to_date = d.to_date
		s.base = d.base
		s.variable = d.variable
		s.company = d.company
		s.save()

	frappe.db.sql("update `tabSalary Structure` set docstatus=1")
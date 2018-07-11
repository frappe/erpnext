# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from datetime import datetime
from erpnext.hr.doctype.salary_structure_assignment.salary_structure_assignment import DuplicateAssignment

def execute():
	frappe.reload_doc("hr", "doctype", "salary_structure_assignment")
	frappe.db.sql("""
		delete from `tabSalary Structure Assignment`
		where salary_structure in (select name from `tabSalary Structure` where is_active='No' or docstatus!=1)
	""")
	for d in frappe.db.sql("""
		select sse.*, ss.company
		from `tabSalary Structure Employee` sse, `tabSalary Structure` ss
		where ss.name = sse.parent AND ss.is_active='Yes'
		AND sse.employee in (select name from `tabEmployee` where ifNull(status, '') != 'Left')""", as_dict=1):
		try:
			s = frappe.new_doc("Salary Structure Assignment")
			s.employee = d.employee
			s.employee_name = d.employee_name
			s.salary_structure = d.parent
			s.from_date = d.from_date
			s.to_date = d.to_date if isinstance(d.to_date, datetime) else None
			s.base = d.base
			s.variable = d.variable
			s.company = d.company

			# to migrate the data of the old employees
			s.flags.old_employee = True
			s.save()
			s.submit()
		except DuplicateAssignment:
			pass

	frappe.db.sql("update `tabSalary Structure` set docstatus=1")
from __future__ import unicode_literals
import frappe
import itertools

def execute():
	salary_structure = frappe.get_all("Salary Structure", filters={"docstatus": 1}, as_list=1)
	salary_structure = list(itertools.chain(*salary_structure))
	salary_structure = "', '".join(map(str, salary_structure))

	query = ''' update `tabSalary Detail` set docstatus=1 where parent in ('{0}')'''.format(salary_structure)
	frappe.db.sql(query)


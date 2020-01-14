from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('Salary Slip')
	if not frappe.db.has_column('Salary Detail', 'abbr'):
		return

	salary_details = frappe.db.sql("""select abbr, salary_component, name from `tabSalary Detail`
				where abbr is null or abbr = ''""", as_dict=True)

	for salary_detail in salary_details:
		salary_component_abbr = frappe.get_value("Salary Component", salary_detail.salary_component, "salary_component_abbr")
		frappe.db.sql("""update `tabSalary Detail` set abbr = %s where name = %s""",(salary_component_abbr, salary_detail.name))
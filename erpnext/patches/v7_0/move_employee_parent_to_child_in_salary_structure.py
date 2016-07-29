import frappe

def execute():
	frappe.reload_doc('hr', 'doctype', 'salary_structure')
	for ss in frappe.db.sql(""" select employee, name from `tabSalary Structure`""", as_dict=True):
		ss_doc = frappe.get_doc('Salary Structure', ss.name)
		se = ss_doc.append('employees',{})
		se.employee = ss.employee
		se.base = 0
		ss_doc.save()
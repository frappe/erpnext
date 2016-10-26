import frappe

def execute():
	frappe.reload_doc('hr', 'doctype', 'salary_structure')
	frappe.reload_doc('hr', 'doctype', 'salary_structure_employee')
	for ss in frappe.db.sql(""" select employee, name from `tabSalary Structure`""", as_dict=True):
		ss_doc = frappe.get_doc('Salary Structure', ss.name)
		salary_employee = ss_doc.append('employees',{})
		salary_employee.employee = ss.employee
		salary_employee.base = 0
		if not ss_doc.company:
			ss_doc.company = frappe.db.get_value('Employee', salary_employee.employee, 'company')
		ss_doc.flags.ignore_validate = True
		ss_doc.flags.ignore_mandatory = True
		ss_doc.save()

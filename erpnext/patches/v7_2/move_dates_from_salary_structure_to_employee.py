import frappe

def execute():
	frappe.reload_doc('hr', 'doctype', 'salary_structure_employee')
	salary_structures = frappe.db.sql("""select name, to_date, from_date from `tabSalary Structure`""", as_dict=True)

	for salary_structure in salary_structures:
		frappe.db.sql(""" update `tabSalary Structure Employee` set from_date = %s, to_date = %s
			where parent = %s """, (salary_structure.from_date, salary_structure.to_date or 'null', salary_structure.name))
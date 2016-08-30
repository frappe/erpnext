import frappe
from frappe.utils import flt

def execute():
	frappe.reload_doc('hr', 'doctype', 'salary_component')
	sal_components = frappe.db.sql("""
		select DISTINCT salary_component, parentfield from `tabSalary Detail`""", as_dict=True)

	if sal_components:
		for sal_component in sal_components:
			if sal_component.parentfield == "earnings":
				frappe.db.sql("""update `tabSalary Component` set type='Earning' where salary_component=%(sal_comp)s""",{"sal_comp": sal_component.salary_component})
			else:
				frappe.db.sql("""update `tabSalary Component` set type='Deduction' where salary_component=%(sal_comp)s""",{"sal_comp": sal_component.salary_component})
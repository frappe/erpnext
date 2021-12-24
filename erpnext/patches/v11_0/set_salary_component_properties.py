from __future__ import unicode_literals

import frappe


def execute():
	frappe.reload_doc('Payroll', 'doctype', 'salary_detail')
	frappe.reload_doc('Payroll', 'doctype', 'salary_component')

	frappe.db.sql("update `tabSalary Component` set is_tax_applicable=1 where type='Earning'")

	frappe.db.sql("""update `tabSalary Component` set variable_based_on_taxable_salary=1
	    where type='Deduction' and name in ('TDS', 'Tax Deducted at Source')""")

	frappe.db.sql("""update `tabSalary Detail` set is_tax_applicable=1
	    where parentfield='earnings' and statistical_component=0""")
	frappe.db.sql("""update `tabSalary Detail` set variable_based_on_taxable_salary=1
	    where parentfield='deductions' and salary_component in ('TDS', 'Tax Deducted at Source')""")

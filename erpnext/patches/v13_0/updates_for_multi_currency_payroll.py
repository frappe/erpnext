# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext

def execute():
	company = erpnext.get_default_company()
	company_currency = erpnext.get_company_currency(company)
	default_payroll_payable_account = frappe.db.get_value('Company', erpnext.get_company_currency(company), 'default_payroll_payable_account')
	frappe.reload_doc('accounts', 'doctype', 'salary_component_account')
	frappe.reload_doc('hr', 'doctype', 'employee_advance')
	frappe.reload_doc('hr', 'doctype', 'leave_enchashment')

	doctype_list = [
		'additional_salary'
		'employee_benefit_application'
		'employee_benefit_claim'
		'employee_incentive'
		'employee_tax_exemption_declaration'
		'employee_tax_exemption_proof_submission'
		'income_tax_slab'
		'payroll_entry'
		'retention_bonus'
		'salary_structure'
		'salary_structure_assignment'
		'salary_slip'
	]

	for doctype in doctype_list:
		frappe.reload_doc('payroll', 'doctype', doctype)

	currency_change_list = [
		'tabLeave Encashment',
		'tabEmployee Benefit Application',
		'tabEmployee Benefit Claim',
		'tabEmployee Incentive',
		'tabEmployee Tax Exemption Declaration',
		'tabEmployee Tax Exemption Proof Submission',
		'tabIncome Tax Slab',
		'tabAdditional Salary',
		'tabRetention Bonus',
		'tabSalary Structure'
	]

	for table in currency_change_list:
		frappe.db.sql("""
			UPDATE `{0}`
			SET currency = '{1}'
		""".format(table, company_currency))

	frappe.db.sql("""
		UPDATE `tabSalary Structure Assignment`
		SET currency = %s, payroll_payable_account = %s
	""", (company_currency, default_payroll_payable_account))

	if frappe.db.has_column('Salary Component Account', 'default_account'):
		frappe.db.sql("""
			UPDATE `tabSalary Component Account`
			SET account = default_account,
		""")

	frappe.db.sql("""
		UPDATE `tabPayroll Entry`
		SET currency = %s, exchange_rate = 1, payroll_payable_account = %s
	""", (company_currency, default_payroll_payable_account))

	frappe.db.sql("""
		UPDATE `tabEmployee Advance`
		SET currency = %s, exchange_rate = 1
	""", (company_currency))

	frappe.db.sql("""
		UPDATE `tabSalary Slip`
		SET currency = %s,
			exchange_rate = 1,
			base_hour_rate = hour_rate,
			base_gross_pay = gross_pay,
			base_total_deduction = total_deduction,
			base_net_pay = net_pay,
			base_rounded_total = rounded_total,
			base_total_in_words = total_in_words
	""", (company_currency))
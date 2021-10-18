# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

import erpnext
from erpnext.regional.india.setup import setup


def execute():

	doctypes = ['salary_component',
		'Employee Tax Exemption Declaration',
		'Employee Tax Exemption Proof Submission',
		'Employee Tax Exemption Declaration Category',
		'Employee Tax Exemption Proof Submission Detail',
		'gratuity_rule',
		'gratuity_rule_slab',
		'gratuity_applicable_component'
	]

	for doctype in doctypes:
		frappe.reload_doc('Payroll', 'doctype', doctype, force=True)


	reports = ['Professional Tax Deductions', 'Provident Fund Deductions', 'E-Invoice Summary']
	for report in reports:
		frappe.reload_doc('Regional', 'Report', report)
		frappe.reload_doc('Regional', 'Report', report)

	if erpnext.get_region() == "India":
		setup(patch=True)

	if frappe.db.exists("Salary Component", "Income Tax"):
		frappe.db.set_value("Salary Component", "Income Tax", "is_income_tax_component", 1)
	if frappe.db.exists("Salary Component", "TDS"):
		frappe.db.set_value("Salary Component", "TDS", "is_income_tax_component", 1)

	components = frappe.db.sql("select name from `tabSalary Component` where variable_based_on_taxable_salary = 1", as_dict=1)
	for component in components:
		frappe.db.set_value("Salary Component", component.name, "is_income_tax_component", 1)

	if erpnext.get_region() == "India":
		if frappe.db.exists("Salary Component", "Provident Fund"):
			frappe.db.set_value("Salary Component", "Provident Fund", "component_type", "Provident Fund")
		if frappe.db.exists("Salary Component", "Professional Tax"):
			frappe.db.set_value("Salary Component", "Professional Tax", "component_type", "Professional Tax")

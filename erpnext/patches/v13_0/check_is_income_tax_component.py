# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, erpnext

def execute():
    frappe.reload_doc('Payroll', 'doctype', 'salary_structure')
    frappe.reload_doc('Payroll', 'doctype', 'salary_component')

    if frappe.db.exists("Salary Component", "Income Tax"):
        frappe.db.set_value("Salary Component", "Income Tax", "is_income_tax_component", 1)
    if frappe.db.exists("Salary Component", "TDS"):
        frappe.db.set_value("Salary Component", "TDS", "is_income_tax_component", 1)

    components = frappe.db.sql("select name from `tabSalary Component` where variable_based_on_taxable_salary = 1", as_dict=1)
    for component in components:
        frappe.db.set_value("Salary Component", component.name, "is_income_tax_component", 1)

    if erpnext.get_region() == "India":
        from erpnext.regional.india.setup import make_custom_fields

        for doctype in ("Employee Tax Exemption Declaration", "Employee Tax Exemption Proof Submission",
                        "Employee Tax Exemption Declaration Category", "Employee Tax Exemption Proof Submission Detail"):
            frappe.reload_doc("Payroll", "doctype", doctype)

        make_custom_fields()

        if frappe.db.exists("Salary Component", "Provident Fund"):
            frappe.db.set_value("Salary Component", "Provident Fund", "component_type", "Provident Fund")
        if frappe.db.exists("Salary Component", "Professional Tax"):
            frappe.db.set_value("Salary Component", "Professional Tax", "component_type", "Professional Tax")

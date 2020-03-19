# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
    payroll_periods =  frappe.db.sql(
        """ Select
            name, company, start_date, end_date, standard_tax_exemption_amount
        FROM `tabPayroll Period`
        ORDER BY start_date DESC
        """, as_dict = 1)

    for i, period in enumerate(payroll_periods):
        income_tax_slab = frappe.new_doc("Income Tax Slab")

        income_tax_slab.name = "Tax Slab:" + period.name

        if i == 0:
            income_tax_slab.disabled = 0
        else:
            income_tax_slab.disabled = 1

        income_tax_slab.effective_from = period.start_date
        income_tax_slab.company = period.company
        income_tax_slab.allow_tax_exemption = 1
        income_tax_slab.standard_tax_exemption_amount = period.standard_tax_exemption_amount

        income_tax_slab.flags.ignore_mandatory = True
        income_tax_slab.submit()

        frappe.db.sql(
        """ UPDATE `tabTaxable Salary Slab`
            SET parent = %s , parentfield = 'slabs' , parenttype = "Income Tax Slab"
        """, income_tax_slab.name, as_dict = 1)

        if i == 0:
            frappe.db.sql("""
                UPDATE
                    `tabSalary Structure Assignment`
                set
                    income_tax_slab = %s
                where
                    company = %s
                    and from_date >= %s
            """, (income_tax_slab.name, income_tax_slab.company, period.start_date))

    #move other incomes to seprate doc.


    employees = [employee.name for employee in frappe.get_all("Employee")]

    proofs = frappe.get_all("Employee Tax Exemption Proof Submission",
        filters = [
            ['employee', 'in', employees],
            ['docstatus', '=', 1]
        ],
        fields =['payroll_period', 'employee', 'company', 'income_from_other_sources'],
    )

    for proof in proofs:
        if proof.income_from_other_sources:
            employee_other_income = frappe.new_doc("Employee Other Income")
            employee_other_income.employee = proof.employee
            employee_other_income.payroll_period = proof.payroll_period
            employee_other_income.company = proof.company
            employee_other_income.amount = proof.income_from_other_sources

        try:
            employee_other_income.submit()
        except:
            pass

        #removeing employee having proof for exemption to get other income form Deceleration
        employees.remove(proof.employee)


    declerations = frappe.get_all("Employee Tax Exemption Declaration",
        filters = [
            ['employee', 'in', employees],
            ['docstatus', '=', 1]
        ],
        fields =['payroll_period', 'employee', 'company', 'income_from_other_sources'],
    )

    for declaration in declerations:
        if declaration.income_from_other_sources:
            employee_other_income = frappe.new_doc("Employee Other Income")
            employee_other_income.employee = declaration.employee
            employee_other_income.payroll_period = declaration.payroll_period
            employee_other_income.company = declaration.company
            employee_other_income.amount = declaration.income_from_other_sources

        try:
            employee_other_income.submit()
        except:
            pass



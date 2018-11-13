# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute():
    '''
	Fields to move from the health insurance to employee insurance doctype

    '''
    if not frappe.db.has_column('Employee', 'health_insurance_provider'):
        return

    frappe.reload_doc('hr', 'doctype', 'employee_insurance')
    frappe.reload_doc('hr', 'doctype', 'insurance_company')
    frappe.reload_doc('hr', 'doctype', 'insurance_type')
    frappe.reload_doc('hr', 'doctype', 'employee')
    frappe.reload_doc('hr', 'doctype', 'additional_salary')

    if frappe.db.a_row_exists('Employee Insurance'): return

    health_ins_record = frappe.get_all("Employee",
        fields = {"employee", "health_insurance_provider", "health_insurance_no"},
        filters = {"health_insurance_provider": ("!=","")})

    if not frappe.db.exists("Insurance Type", _("Health Insurance")):
        ins_type = frappe.new_doc("Insurance Type")
        ins_type.name = _("Health Insurance")
        ins_type.save()

    for h in health_ins_record:
        try:
            ins_company = frappe.new_doc("Insurance Company")
            ins_company.name = h.health_insurance_provider
            ins_company.save()
        except frappe.DuplicateEntryError:
            pass

        employee_insurance = frappe.new_doc("Employee Insurance")
        employee_insurance.employee = h.employee
        employee_insurance.insurance_company = ins_company.name
        employee_insurance.insurance_type = ins_type.name
        employee_insurance.policy_no = h.health_insurance_no
        employee_insurance.flags.ignore_mandatory = True
        employee_insurance.insert()
        employee_insurance.submit()

    if frappe.db.exists("DocType", "Employee Health Insurance"):
        frappe.delete_doc("DocType", "Employee Health Insurance")

    if frappe.db.exists("DocType", "Health Insurance"):
        frappe.delete_doc("DocType", "Health Insurance")
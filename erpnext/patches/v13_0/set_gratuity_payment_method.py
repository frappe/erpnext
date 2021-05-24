from __future__ import unicode_literals
import frappe

def execute():
    frappe.reload_doctype("Gratuity")

    frappe.db.sql("update `tabGratuity` set `payment_method` = 'Additional Salary' where `pay_via_salary_slip` = 1")
    frappe.db.sql("update `tabGratuity` set `payment_method` = 'Payment Entry' where `pay_via_salary_slip` = 0")

from __future__ import unicode_literals
import frappe

def execute():
    # frappe.reload_doc('HR', 'doctype', 'leave_application')
    frappe.db.sql("""
            UPDATE `tabLeave Application` SET 
            status = 'Cancelled'
            WHERE status = 'Approved' and docstatus = 2
            """)
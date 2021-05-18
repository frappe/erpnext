from __future__ import unicode_literals
import frappe

def execute():

    frappe.reload_doc("HR", "doctype", "HR Settings")
    restrict_backdated = frappe.db.sql("select value from `tabSingles` where doctype = 'Hr Settings' and field = 'restrict_backdated_leave_application';" , as_dict=1)[0].value
    allowed_role = frappe.db.sql("select value from `tabSingles` where doctype = 'Hr Settings' and field = 'role_allowed_to_create_backdated_leave_application';" , as_dict=1)[0].value

    if int(restrict_backdated):
        frappe.db.set_value("HR Settings", None, "allow_backdated_leave_application", 0)
        frappe.db.set_value("HR Settings", None, "role_allowed_to_create_backdated_leave_application", allowed_role)
    else:
        frappe.db.set_value("HR Settings", None, "allow_backdated_leave_application", 1)

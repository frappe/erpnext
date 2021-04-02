from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("hr", "doctype", "hr_settings")
	frappe.db.set_value("HR Settings", None, "show_leaves_of_all_department_members_in_calendar", 1)
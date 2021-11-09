import frappe


def execute():
	frappe.reload_doc("hr", "doctype", "hr_settings")
	frappe.db.set_value("HR Settings", None, "payroll_based_on", "Leave")

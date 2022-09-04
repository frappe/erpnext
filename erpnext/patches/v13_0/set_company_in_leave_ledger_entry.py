import frappe


def execute():
	frappe.reload_doc("HR", "doctype", "Leave Allocation")
	frappe.reload_doc("HR", "doctype", "Leave Ledger Entry")
	frappe.db.sql(
		"""update `tabLeave Ledger Entry` as lle set company = (select company from `tabEmployee` where employee = lle.employee)"""
	)
	frappe.db.sql(
		"""update `tabLeave Allocation` as la set company = (select company from `tabEmployee` where employee = la.employee)"""
	)

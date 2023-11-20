import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "accounts_settings")
	frappe.db.set_single_value("Accounts Settings", "manipulate_grand_total_for_inclusive_tax", 1)

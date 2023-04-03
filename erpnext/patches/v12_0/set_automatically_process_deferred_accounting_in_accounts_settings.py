import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "accounts_settings")

	frappe.db.set_value(
		"Accounts Settings", None, "automatically_process_deferred_accounting_entry", 1
	)

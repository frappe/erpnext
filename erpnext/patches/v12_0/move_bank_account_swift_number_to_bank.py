import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "bank", force=1)

	if (
		frappe.db.table_exists("Bank")
		and frappe.db.table_exists("Bank Account")
		and frappe.db.has_column("Bank Account", "swift_number")
	):
		try:
			frappe.db.sql(
				"""
				UPDATE `tabBank` b, `tabBank Account` ba
				SET b.swift_number = ba.swift_number WHERE b.name = ba.bank
			"""
			)
		except Exception as e:
			frappe.log_error("Bank to Bank Account patch migration failed")

	frappe.reload_doc("accounts", "doctype", "bank_account")
	frappe.reload_doc("accounts", "doctype", "payment_request")

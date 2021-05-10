import frappe


def execute():
	frappe.reload_doctype("Stock Ledger Entry")
	frappe.reload_doctype("Stock Reconciliation")

	frappe.db.sql("""
		update  `tabStock Ledger Entry` sle 
		set sle.reset_rate = 1
		where voucher_type = 'Stock Reconciliation'
	""")

	frappe.db.sql("""
		update `tabStock Reconciliation`
		set
			reset_rate = 1
	""")

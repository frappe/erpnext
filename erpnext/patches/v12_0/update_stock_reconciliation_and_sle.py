import frappe


def execute():
	frappe.reload_doctype("Stock Ledger Entry")
	frappe.reload_doctype("Stock Reconciliation")

	frappe.db.sql("""
		update  `tabStock Ledger Entry` sle 
		inner join `tabStock Reconciliation` sr on sr.name=sle.voucher_no
		set sle.reset_rate = 1
	""")

	frappe.db.sql("""
		update `tabStock Reconciliation`
		set
			reset_rate = 1
	""")

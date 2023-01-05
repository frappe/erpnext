import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "stock_ledger_entry")
	frappe.db.sql("""
		update `tabStock Ledger Entry`
		set hu_qty_after_transaction = qty_after_transaction
	""")

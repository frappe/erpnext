import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "stock_ledger_entry")
	frappe.db.sql("""
		update `tabStock Ledger Entry`
		set packed_qty_after_transaction = batch_qty_after_transaction, is_processed = 1
	""")

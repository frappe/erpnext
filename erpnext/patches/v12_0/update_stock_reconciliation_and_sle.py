import frappe


def execute():
	frappe.reload_doctype("Stock Ledger Entry")
	frappe.reload_doctype("Stock Reconciliation")
	frappe.reload_doctype("Stock Reconciliation Item")

	frappe.db.sql("""
		update  `tabStock Ledger Entry` sle 
		set sle.reset_rate = 1
		where voucher_type = 'Stock Reconciliation'
	""")

	frappe.db.sql("""
		update `tabStock Reconciliation` set reset_rate = 1
	""")

	frappe.db.sql("""
		update `tabStock Reconciliation Item` sri
		inner join `tabItem` item on item.name = sri.item_code
		set sri.total_qty = sri.qty, sri.conversion_factor = 1, sri.stock_uom = item.stock_uom, sri.loose_uom = item.stock_uom
	""")

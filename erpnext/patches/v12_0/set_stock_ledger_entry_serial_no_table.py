import frappe

def execute():
	frappe.reload_doc("stock", "doctype", "stock_ledger_entry_serial_no")
	frappe.reload_doc("stock", "doctype", "stock_ledger_entry")

	sles = frappe.get_all("Stock Ledger Entry", filters={"serial_no": ['is', 'set']})
	for sle in sles:
		sle_doc = frappe.get_doc("Stock Ledger Entry", sle.name)
		sle_doc.set_serial_no_table()
		for d in sle_doc.serial_numbers:
			d.owner = sle_doc.owner
			d.db_insert()

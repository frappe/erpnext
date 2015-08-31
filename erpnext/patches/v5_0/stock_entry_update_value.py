import frappe

def execute():
	for d in frappe.db.get_all("Stock Entry"):
		se = frappe.get_doc("Stock Entry", d.name)
		se.set_total_incoming_outgoing_value()
		se.db_update()

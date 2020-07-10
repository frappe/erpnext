import frappe

def execute():
	frappe.db.sql("""
		DELETE FROM `tabReport`
		WHERE name = 'Requested Items to Order'
	""")
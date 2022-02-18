import frappe


def execute():
	frappe.db.sql("""
		update tabCustomer
		set represents_company = NULL
		where represents_company = ''
	""")

import frappe

def execute():
	frappe.reload_doc("account", "doctype", "budget")
	frappe.db.sql("""
		update
			`tabBudget`
		set
			budget_against = 'Cost Center'
		""")

import frappe

def execute():
	frappe.db.sql("""update tabContact, tabUser set tabContact.user = tabUser.name
		where tabContact.email_id = tabUser.email""")

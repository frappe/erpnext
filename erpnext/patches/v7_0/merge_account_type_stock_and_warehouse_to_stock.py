import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "account")
	
	frappe.db.sql(""" update tabAccount set account_type = "Stock"
		where account_type = "Warehouse" """)
	
	frappe.db.commit()
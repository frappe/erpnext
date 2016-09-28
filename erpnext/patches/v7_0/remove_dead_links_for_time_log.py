import frappe

def execute():
	frappe.db.sql("""UPDATE tabCommunication 
				SET reference_doctype = NULL,
				reference_name = NULL
				WHERE reference_doctype = "Time Log" """, auto_commit=1)
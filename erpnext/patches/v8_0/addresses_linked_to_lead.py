import frappe

def execute():
	frappe.db.sql("""UPDATE `tabDynamic Link` SET link_doctype = 'Lead' WHERE link_doctype = 'Load'""")

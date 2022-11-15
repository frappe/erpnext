import frappe

def execute():
	frappe.reload_doctype("Currency Exchange")
	frappe.db.sql("""
		update `tabCurrency Exchange` 
		set `date` = '2010-01-01' 
		where date is null or date = '0000-00-00'
	""")
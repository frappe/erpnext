import frappe

def execute():
	for e in frappe.db.sql_list("""select name from tabEvent where
		repeat_on='Every Year' and ref_type='Employee'"""):
		frappe.delete_doc("Event", e, force=True)

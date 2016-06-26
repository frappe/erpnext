import frappe

def execute():
	frappe.reload_doc("stock", "doctype", "warehouse")
	
	frappe.db.sql("""update tabWarehouse set is_group = if (is_group="Yes", 1, 0)""")
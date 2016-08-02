from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Item")
	if "default_bom" in frappe.db.get_table_columns("Item"):
		frappe.db.sql("""update `tabItem` 
			set default_material_request_type = (
				case 
					when (default_bom is not null and default_bom != '')
					then 'Manufacture' 
					else 'Purchase' 
				end )""")
				
	else:
		frappe.db.sql("update tabItem set default_material_request_type='Purchase'")
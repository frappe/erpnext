import frappe

def execute():
	frappe.db.sql("""
		update tabAsset a
		set calculate_depreciation = 1
		where exists(select ds.name from `tabDepreciation Schedule` ds where ds.parent=a.name)
	""")
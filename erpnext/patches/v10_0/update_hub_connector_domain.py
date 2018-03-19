import frappe

def execute():
	if frappe.db.table_exists("Data Migration Connector"):
		frappe.db.sql("""
			UPDATE `tabData Migration Connector`
			SET hostname = 'https://hubmarket.org'
			WHERE connector_name = 'Hub Connector'
		""")
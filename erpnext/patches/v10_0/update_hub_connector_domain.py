import frappe

def execute():
    frappe.db.sql("""
        UPDATE `tabData Migration Connector`
        SET hostname = 'https://hubmarket.org'
        WHERE connector_name = 'Hub Connector'
    """)
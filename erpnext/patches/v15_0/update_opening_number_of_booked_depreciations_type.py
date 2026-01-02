import frappe

def execute():
    frappe.db.sql("""
        ALTER TABLE `tabAsset Depreciation Schedule`
        MODIFY COLUMN opening_number_of_booked_depreciations DECIMAL(21,9) NOT NULL DEFAULT 0.000000000
    """)
    frappe.db.commit()
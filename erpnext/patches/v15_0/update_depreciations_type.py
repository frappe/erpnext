import frappe

def execute():
    frappe.db.sql("""
        ALTER TABLE `tabAsset Finance Book`
        MODIFY COLUMN total_number_of_depreciations DECIMAL(21,9) NOT NULL DEFAULT 0.000000000,
        MODIFY COLUMN total_number_of_booked_depreciations DECIMAL(21,9) NOT NULL DEFAULT 0.000000000
    """)
    frappe.db.commit()
    frappe.clear_cache()
    frappe.msgprint("Patch executed successfully")
import frappe


def execute():
    frappe.reload_doc("manufacturing", "doctype", "bom_operation")
    frappe.reload_doc("manufacturing", "doctype", "work_order_operation")

    frappe.db.sql("""
        UPDATE
            `tabBOM Operation` bo
        SET
            bo.batch_size = 1
    """)
    frappe.db.sql("""
        UPDATE
            `tabWork Order Operation` wop
        SET
            wop.batch_size = 1
    """)

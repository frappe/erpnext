import frappe

def execute():
    """ copy data from old fields to new """
    frappe.reload_doc("projects", "doctype", "project")

    frappe.db.sql("""update `tabProject`
        set
            total_sales_amount = total_sales_cost,
            total_billable_amount = total_billing_amount
    """)
import frappe

def execute():
    # renamed default status to Completed as status "Closed" is ambiguous
    frappe.db.sql('update tabTask set status = "Completed" where status = "Closed"')
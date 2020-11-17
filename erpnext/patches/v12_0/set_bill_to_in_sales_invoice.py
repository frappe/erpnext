import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "sales_invoice")
	frappe.db.sql("update `tabSales Invoice` set bill_to = customer")
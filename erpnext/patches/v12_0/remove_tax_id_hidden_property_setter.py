import frappe

def execute():
	frappe.delete_doc_if_exists("Property Setter", "Sales Order-tax_id-hidden")
	frappe.delete_doc_if_exists("Property Setter", "Delivery Note-tax_id-hidden")
	frappe.delete_doc_if_exists("Property Setter", "Sales Invoice-tax_id-hidden")

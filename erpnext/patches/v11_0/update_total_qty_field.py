import frappe

def execute():
	frappe.reload_doc('buying', 'doctype', 'purchase_order')
	frappe.reload_doc('buying', 'doctype', 'supplier_quotation')
	frappe.reload_doc('selling', 'doctype', 'sales_order')
	frappe.reload_doc('selling', 'doctype', 'quotation')
	frappe.reload_doc('stock', 'doctype', 'delivery_note')
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice')

	doctypes = ['Sales Order', 'Sales Invoice', 'Delivery Note',\
		'Purchase Order', 'Purchase Invoice', 'Purchase Receipt', 'Quotation', 'Supplier Quotation']

	

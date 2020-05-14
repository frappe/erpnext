from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "sales_taxes_and_charges_template")
	
	# set add_deduct_tax in Sales Taxes And Charges Templates
	if frappe.db.has_column("Sales Taxes and Charges", "category") and\
		frappe.db.has_column("Sales Taxes and Charges", "add_deduct_tax"):
		frappe.db.sql('''update `tabSales Taxes and Charges`
			set category = 'Total',
			add_deduct_tax = 'Add'
		''')
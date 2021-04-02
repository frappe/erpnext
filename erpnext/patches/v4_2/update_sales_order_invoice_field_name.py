from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	frappe.db.sql("""update `tabSales Invoice` set from_date = invoice_period_from_date,
		to_date = invoice_period_to_date, is_recurring = convert_into_recurring_invoice""")

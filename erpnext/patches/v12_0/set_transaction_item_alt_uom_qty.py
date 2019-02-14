# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('selling', 'doctype', 'quotation_item')
	frappe.reload_doc('selling', 'doctype', 'sales_order_item')
	frappe.reload_doc('stock', 'doctype', 'delivery_note_item')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice_item')
	frappe.reload_doc('buying', 'doctype', 'supplier_quotation_item')
	frappe.reload_doc('buying', 'doctype', 'purchase_order_item')
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt_item')
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice_item')

	doctypes = [
		'Sales Order', 'Delivery Note', 'Sales Invoice',
		'Purchase Order', 'Purchase Receipt', 'Purchase Invoice',
		'Quotation', 'Supplier Quotation'
	]

	# Calculate and update database
	for dt in doctypes:
		docnames = frappe.get_all(dt)

		frappe.db.sql("""
			update `tab{dt} Item`
			set alt_uom_size = 1, alt_uom_qty = stock_qty
			where ifnull(alt_uom, '') = ''
		""".format(dt=dt))
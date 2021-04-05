# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

def execute():
	frappe.reload_doc('selling', 'doctype', 'quotation')
	frappe.reload_doc('selling', 'doctype', 'quotation_item')
	frappe.reload_doc('selling', 'doctype', 'sales_order')
	frappe.reload_doc('selling', 'doctype', 'sales_order_item')
	frappe.reload_doc('stock', 'doctype', 'delivery_note')
	frappe.reload_doc('stock', 'doctype', 'delivery_note_item')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice_item')
	frappe.reload_doc('buying', 'doctype', 'supplier_quotation')
	frappe.reload_doc('buying', 'doctype', 'supplier_quotation_item')
	frappe.reload_doc('buying', 'doctype', 'purchase_order')
	frappe.reload_doc('buying', 'doctype', 'purchase_order_item')
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt')
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt_item')
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice')
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice_item')

	doctypes = [
		'Sales Order', 'Delivery Note', 'Sales Invoice',
		'Purchase Order', 'Purchase Receipt', 'Purchase Invoice',
		'Quotation', 'Supplier Quotation'
	]

	frappe.db.auto_commit_on_many_writes = True

	# Calculate and update database
	for dt in doctypes:
		print(dt + " Started")

		# Copy item_tax_detail into item_tax_detail_before_discount
		frappe.db.sql("""
			update `tab{0} Item` set item_tax_detail_before_discount = item_tax_detail
		""".format(dt))

		# Get documents to modify programatically
		docnames = frappe.db.sql_list("""
			select p.name
			from `tab{0}` p
			where p.discount_amount != 0 and p.total_taxes_and_charges != 0
		""".format(dt))

		for dn in docnames:
			doc = frappe.get_doc(dt, dn)
			calculate_taxes_and_totals(doc)

			for item in doc.items:
				frappe.db.set_value(dt + " Item", item.name, "item_tax_detail_before_discount", item.item_tax_detail_before_discount, update_modified=False)

			doc.clear_cache()

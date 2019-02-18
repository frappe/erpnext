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
	frappe.reload_doc('accounts', 'doctype', 'sales_taxes_and_charges')
	frappe.reload_doc('accounts', 'doctype', 'purchase_taxes_and_charges')

	doctypes = [
		'Sales Order', 'Delivery Note', 'Sales Invoice',
		'Purchase Order', 'Purchase Receipt', 'Purchase Invoice',
		'Quotation', 'Supplier Quotation'
	]

	new_item_fields = [
		'tax_exclusive_price_list_rate',
		'tax_exclusive_rate',
		'tax_exclusive_amount',
		'tax_exclusive_discount_amount',
		'tax_exclusive_rate_with_margin'
	]
	new_item_fields += ['base_' + f for f in new_item_fields]
	new_item_fields = set(new_item_fields)

	# Calculate and update database
	for dt in doctypes:
		docnames = frappe.get_all(dt)
		for dn in docnames:
			dn = dn.name
			doc = frappe.get_doc(dt, dn)
			calculate_taxes_and_totals(doc)

			frappe.db.set_value(dt, doc.name, {
				"tax_exclusive_total": doc.tax_exclusive_total,
				"base_tax_exclusive_total": doc.base_tax_exclusive_total
			}, None, update_modified=False)

			for item in doc.items:
				item_fields = set([f.fieldname for f in item.meta.fields])
				fields_to_update = list(new_item_fields.intersection(item_fields))
				values_to_update = [item.get(f) for f in fields_to_update]
				update_dict = dict(zip(fields_to_update, values_to_update))
				frappe.db.set_value(dt + " Item", item.name, update_dict, None, update_modified=False)

			for tax in doc.taxes:
				frappe.db.set_value(tax.doctype, tax.name, "total_before_discount_amount", tax.total_before_discount_amount)

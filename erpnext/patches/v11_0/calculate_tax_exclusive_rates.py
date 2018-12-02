# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

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

	new_fields = [
		'tax_exclusive_price_list_rate',
		'tax_exclusive_rate',
		'tax_exclusive_amount',
		'tax_exclusive_discount_amount',
		'tax_exclusive_rate_with_margin'
	]
	new_fields += ['base_' + f for f in new_fields]
	new_fields = set(new_fields)

	# Calculate and update database
	for dt in doctypes:
		docnames = frappe.get_all(dt)
		for dn in docnames:
			dn = dn.name
			doc = frappe.get_doc(dt, dn)
			calculate_taxes_and_totals(doc)
			for item in doc.items:
				item_fields = set([f.fieldname for f in item.meta.fields])
				fields_to_update = list(new_fields.intersection(item_fields))
				values_to_update = [item.get(f) for f in fields_to_update]
				update_dict = dict(zip(fields_to_update, values_to_update))
				frappe.db.set_value(dt + " Item", item.name, update_dict, None, update_modified=False)

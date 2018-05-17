from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	to_rename = ['Purchase Order', 'Journal Entry', 'Sales Invoice', 'Payment Entry',
		'Delivery Note', 'Purchase Invoice', 'Quotation', 'Sales Order',
		'Purchase Receipt', 'Supplier Quotation']

	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice')
	frappe.reload_doc('accounts', 'doctype', 'payment_entry')
	frappe.reload_doc('accounts', 'doctype', 'journal_entry')
	frappe.reload_doc('buying', 'doctype', 'purchase_order')
	frappe.reload_doc('buying', 'doctype', 'supplier_quotation')
	frappe.reload_doc('desk', 'doctype', 'auto_repeat')
	frappe.reload_doc('selling', 'doctype', 'quotation')
	frappe.reload_doc('selling', 'doctype', 'sales_order')
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt')
	frappe.reload_doc('stock', 'doctype', 'delivery_note')

	for doctype in to_rename:
		if frappe.db.has_column(doctype, 'subscription'):
			rename_field(doctype, 'subscription', 'auto_repeat')

	subscriptions = frappe.db.sql('select * from `tabSubscription`', as_dict=1)

	for doc in subscriptions:
		doc['doctype'] = 'Auto Repeat'
		auto_repeat = frappe.get_doc(doc)
		auto_repeat.db_insert()

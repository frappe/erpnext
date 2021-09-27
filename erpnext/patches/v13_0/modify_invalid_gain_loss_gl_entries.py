from __future__ import unicode_literals

import json

import frappe


def execute():
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice_advance')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice_advance')

	purchase_invoices = frappe.db.sql("""
		select
			parenttype as type, parent as name
		from
			`tabPurchase Invoice Advance`
		where
			ref_exchange_rate = 1
			and docstatus = 1
			and ifnull(exchange_gain_loss, '') != ''
		group by
			parent
	""", as_dict=1)

	sales_invoices = frappe.db.sql("""
		select
			parenttype as type, parent as name
		from
			`tabSales Invoice Advance`
		where
			ref_exchange_rate = 1
			and docstatus = 1
			and ifnull(exchange_gain_loss, '') != ''
		group by
			parent
	""", as_dict=1)

	if purchase_invoices + sales_invoices:
		frappe.log_error(json.dumps(purchase_invoices + sales_invoices, indent=2), title="Patch Log")

	for invoice in purchase_invoices + sales_invoices:
		doc = frappe.get_doc(invoice.type, invoice.name)
		doc.docstatus = 2
		doc.make_gl_entries()
		for advance in doc.advances:
			if advance.ref_exchange_rate == 1:
				advance.db_set('exchange_gain_loss', 0, False)
		doc.docstatus = 1
		doc.make_gl_entries()
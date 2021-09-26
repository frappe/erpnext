from __future__ import unicode_literals

import frappe


def execute():
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

	for invoice in purchase_invoices + sales_invoices:
		doc = frappe.get_doc(invoice.type, invoice.name)
		doc.docstatus = 2
		doc.make_gl_entries()
		for advance in doc.advances:
			advance.db_set('exchange_gain_loss', 0, False)
		doc.docstatus = 1
		doc.make_gl_entries()
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc('stock', 'doctype', 'delivery_note_item')

	frappe.db.sql("""update `tabDelivery Note Item` set so_detail = prevdoc_detail_docname
		where ifnull(against_sales_order, '') != ''""")

	frappe.db.sql("""update `tabDelivery Note Item` set si_detail = prevdoc_detail_docname
		where ifnull(against_sales_invoice, '') != ''""")

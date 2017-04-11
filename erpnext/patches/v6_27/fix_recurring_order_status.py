# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for doc in (
		{
			"doctype": "Sales Order",
			"stock_doctype": "Delivery Note",
			"invoice_doctype": "Sales Invoice",
			"stock_doctype_ref_field": "against_sales_order",
			"invoice_ref_field": "sales_order",
			"qty_field": "delivered_qty"
		},
		{
			"doctype": "Purchase Order",
			"stock_doctype": "Purchase Receipt",
			"invoice_doctype": "Purchase Invoice",
			"stock_doctype_ref_field": "prevdoc_docname",
			"invoice_ref_field": "purchase_order",
			"qty_field": "received_qty"
		}):

		order_list = frappe.db.sql("""select name from `tab{0}`
			where docstatus=1 and is_recurring=1
			and ifnull(recurring_id, '') != name and creation >= '2016-01-25'"""
			.format(doc["doctype"]), as_dict=1)

		for order in order_list:
			frappe.db.sql("""update `tab{0} Item`
				set {1}=0, billed_amt=0 where parent=%s""".format(doc["doctype"],
					doc["qty_field"]), order.name)

			# Check against Delivery Note and Purchase Receipt
			stock_doc_list = frappe.db.sql("""select distinct parent from `tab{0} Item`
				where docstatus=1 and ifnull({1}, '')=%s"""
				.format(doc["stock_doctype"], doc["stock_doctype_ref_field"]), order.name)

			if stock_doc_list:
				for dn in stock_doc_list:
					frappe.get_doc(doc["stock_doctype"], dn[0]).update_qty(update_modified=False)

			# Check against Invoice
			invoice_list = frappe.db.sql("""select distinct parent from `tab{0} Item`
				where docstatus=1 and ifnull({1}, '')=%s"""
				.format(doc["invoice_doctype"], doc["invoice_ref_field"]), order.name)

			if invoice_list:
				for dn in invoice_list:
					frappe.get_doc(doc["invoice_doctype"], dn[0]).update_qty(update_modified=False)

			frappe.get_doc(doc["doctype"], order.name).set_status(update=True, update_modified=False)
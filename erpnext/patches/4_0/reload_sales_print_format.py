# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('accounts', 'Print Format', 'POS Invoice')
	frappe.reload_doc('accounts', 'Print Format', 'Sales Invoice Classic')
	frappe.reload_doc('accounts', 'Print Format', 'Sales Invoice Modern')
	frappe.reload_doc('accounts', 'Print Format', 'Sales Invoice Spartan')
	frappe.reload_doc('selling', 'Print Format', 'Quotation Classic')
	frappe.reload_doc('selling', 'Print Format', 'Quotation Modern')
	frappe.reload_doc('selling', 'Print Format', 'Quotation Spartan')
	frappe.reload_doc('selling', 'Print Format', 'Sales Order Classic')
	frappe.reload_doc('selling', 'Print Format', 'Sales Order Modern')
	frappe.reload_doc('selling', 'Print Format', 'Sales Order Spartan')
	frappe.reload_doc('stock', 'Print Format', 'Delivery Note Classic')
	frappe.reload_doc('stock', 'Print Format', 'Delivery Note Modern')
	frappe.reload_doc('stock', 'Print Format', 'Delivery Note Spartan')
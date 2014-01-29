# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc('accounts', 'doctype', 'purchase_invoice')
	webnotes.reload_doc('buying', 'doctype', 'purchase_order')
	webnotes.reload_doc('buying', 'doctype', 'supplier_quotation')
	webnotes.reload_doc('stock', 'doctype', 'purchase_receipt')
	webnotes.reload_doc('buying', 'Print Format', 'Purchase Order Classic')
	webnotes.reload_doc('buying', 'Print Format', 'Purchase Order Modern')
	webnotes.reload_doc('buying', 'Print Format', 'Purchase Order Spartan')
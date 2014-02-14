# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc('accounts', 'Print Format', 'POS Invoice')
	webnotes.reload_doc('accounts', 'Print Format', 'Sales Invoice Classic')
	webnotes.reload_doc('accounts', 'Print Format', 'Sales Invoice Modern')
	webnotes.reload_doc('accounts', 'Print Format', 'Sales Invoice Spartan')
	webnotes.reload_doc('selling', 'Print Format', 'Quotation Classic')
	webnotes.reload_doc('selling', 'Print Format', 'Quotation Modern')
	webnotes.reload_doc('selling', 'Print Format', 'Quotation Spartan')
	webnotes.reload_doc('selling', 'Print Format', 'Sales Order Classic')
	webnotes.reload_doc('selling', 'Print Format', 'Sales Order Modern')
	webnotes.reload_doc('selling', 'Print Format', 'Sales Order Spartan')
	webnotes.reload_doc('stock', 'Print Format', 'Delivery Note Classic')
	webnotes.reload_doc('stock', 'Print Format', 'Delivery Note Modern')
	webnotes.reload_doc('stock', 'Print Format', 'Delivery Note Spartan')
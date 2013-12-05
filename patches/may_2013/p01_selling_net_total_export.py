# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint

def execute():
	for module, doctype in (("Accounts", "Sales Invoice"), ("Selling", "Sales Order"), ("Selling", "Quotation"), 
		("Stock", "Delivery Note")):
			webnotes.reload_doc(module, "DocType", doctype)
			webnotes.conn.sql("""update `tab%s` 
				set net_total_export = round(net_total / if(conversion_rate=0, 1, ifnull(conversion_rate, 1)), 2),
				other_charges_total_export = round(grand_total_export - net_total_export, 2)""" %
				(doctype,))
	
	for module, doctype in (("Accounts", "Sales Invoice Item"), ("Selling", "Sales Order Item"), ("Selling", "Quotation Item"), 
		("Stock", "Delivery Note Item")):
			webnotes.reload_doc(module, "DocType", doctype)
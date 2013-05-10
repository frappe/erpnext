from __future__ import unicode_literals
import webnotes

def execute():
	for module, doctype in (("Accounts", "Sales Invoice"), ("Selling", "Sales Order"), ("Selling", "Quotation"), 
		("Stock", "Delivery Note")):
			webnotes.reload_doc(module, "DocType", doctype)
			webnotes.conn.sql("""update `tab%s` 
				set net_total_export = round(net_total / if(conversion_rate=0, 1, ifnull(conversion_rate, 1)), 2)""" %
				(doctype,))
# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("stock", "doctype", "delivery_note_item")
	webnotes.conn.sql("""update `tabDelivery Note Item` set against_sales_order=prevdoc_docname
		where prevdoc_doctype='Sales Order' """)
		
	webnotes.conn.sql("""update `tabDelivery Note Item` set against_sales_invoice=prevdoc_docname
		where prevdoc_doctype='Sales Invoice' """)
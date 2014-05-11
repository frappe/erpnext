# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes, os

def execute():
	webnotes.reload_doc("core", "doctype", "doctype")
	
	tables = webnotes.conn.sql_list("show tables")
	
	if "tabPacked Item" not in tables:
		webnotes.rename_doc("DocType", "Delivery Note Packing Item", "Packed Item", force=True)
	
	webnotes.reload_doc("stock", "doctype", "packed_item")
	
	if os.path.exists("app/stock/doctype/delivery_note_packing_item"):
		os.system("rm -rf app/stock/doctype/delivery_note_packing_item")
	
	if webnotes.conn.exists("DocType", "Delivery Note Packing Item"):
			webnotes.delete_doc("DocType", "Delivery Note Packing Item")
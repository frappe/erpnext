# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("selling", "doctype", "shopping_cart_price_list")
	webnotes.reload_doc("stock", "doctype", "item_price")
	
	for t in [
			("Supplier Quotation", "price_list_name", "buying_price_list"),
			("Purchase Order", "price_list_name", "buying_price_list"),
			("Purchase Invoice", "price_list_name", "buying_price_list"),
			("Purchase Receipt", "price_list_name", "buying_price_list"),
			("Quotation", "price_list_name", "selling_price_list"),
			("Sales Order", "price_list_name", "selling_price_list"),
			("Delivery Note", "price_list_name", "selling_price_list"),
			("Sales Invoice", "price_list_name", "selling_price_list"),
			("POS Setting", "price_list_name", "selling_price_list"),
			("Shopping Cart Price List", "price_list", "selling_price_list"),
			("Item Price", "price_list_name", "price_list"),
			("BOM", "price_list", "buying_price_list"),
		]:
		table_columns = webnotes.conn.get_table_columns(t[0])
		if t[2] in table_columns and t[1] in table_columns:
			# already reloaded, so copy into new column and drop old column
			webnotes.conn.sql("""update `tab%s` set `%s`=`%s`""" % (t[0], t[2], t[1]))
			webnotes.conn.sql_ddl("""alter table `tab%s` drop column `%s`""" % (t[0], t[1]))
		elif t[1] in table_columns:
			webnotes.conn.sql_ddl("alter table `tab%s` change `%s` `%s` varchar(180)" % t)

		webnotes.reload_doc(webnotes.conn.get_value("DocType", t[0], "module"), "DocType", t[0])
		
	webnotes.conn.sql("""update tabSingles set field='selling_price_list'
		where field='price_list_name' and doctype='Selling Settings'""")
	
	webnotes.reload_doc("Selling", "DocType", "Selling Settings")
	webnotes.bean("Selling Settings").save()
	
	

# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint

def execute():
	webnotes.reload_doc("stock", "doctype", "price_list")
	webnotes.reload_doc("stock", "doctype", "item_price")
	
	try:
		for price_list in webnotes.conn.sql_list("""select name from `tabPrice List`"""):
			buying, selling = False, False
			for b, s in webnotes.conn.sql("""select distinct buying, selling 
				from `tabItem Price` where price_list_name=%s""", price_list):
					buying = buying or cint(b)
					selling = selling or cint(s)
		
			buying_or_selling = "Selling" if selling else "Buying"
			webnotes.conn.set_value("Price List", price_list, "buying_or_selling", buying_or_selling)
	except webnotes.SQLError, e:
		if e.args[0] == 1054:
			webnotes.conn.sql("""update `tabPrice List` set buying_or_selling='Selling' 
				where ifnull(buying_or_selling, '')='' """)
		else:
			raise
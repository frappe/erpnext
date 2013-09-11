# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import cint

def execute():
	webnotes.reload_doc("setup", "doctype", "price_list")
	webnotes.reload_doc("setup", "doctype", "item_price")
	
	for price_list in webnotes.conn.sql_list("""select name from `tabPrice List`"""):
		buying, selling = False, False
		for b, s in webnotes.conn.sql("""select distinct buying, selling 
			from `tabItem Price` where price_list_name=%s""", price_list):
				buying = buying or cint(b)
				selling = selling or cint(s)
		
		buying_or_selling = "Buying" if buying else "Selling"
		webnotes.conn.set_value("Price List", price_list, "buying_or_selling", buying_or_selling)

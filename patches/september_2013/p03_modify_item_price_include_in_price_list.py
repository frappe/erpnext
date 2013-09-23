# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("setup", "doctype", "price_list")
	webnotes.reload_doc("setup", "doctype", "item_price")
	webnotes.reload_doc("stock", "doctype", "item")
	
	webnotes.conn.sql("""update `tabItem Price` set parenttype='Price List', 
		parentfield='item_prices', `item_code`=`parent`""")
	
	# re-arranging idx of items
	webnotes.conn.sql("""update `tabItem Price` set `parent`=`price_list`, idx=0""")
	for pl in webnotes.conn.sql("""select name from `tabPrice List`"""):
		webnotes.conn.sql("""set @name=0""")
		webnotes.conn.sql("""update `tabItem Price` set idx = @name := IF(ISNULL( @name ), 0, @name + 1) 
			where idx=0 and parent=%s""", pl[0])
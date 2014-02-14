# Copyright (c) 2014, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("stock", "doctype", "price_list")
	webnotes.reload_doc("stock", "doctype", "item_price")

	if "buying_or_selling" in webnotes.conn.get_table_columns("Price List"):
		webnotes.conn.sql("""update `tabPrice List` set 
			selling = 
				case 
					when buying_or_selling='Selling' 
					then 1 
				end, 
			buying = 
				case 
					when buying_or_selling='Buying' 
					then 1 
				end
			""")
		webnotes.conn.sql("""update `tabItem Price` ip, `tabPrice List` pl 
			set ip.buying=pl.buying, ip.selling=pl.selling
			where ip.price_list=pl.name""")

	webnotes.conn.sql("""update `tabItem Price` set selling=1 where ifnull(selling, 0)=0 and 
		ifnull(buying, 0)=0""")
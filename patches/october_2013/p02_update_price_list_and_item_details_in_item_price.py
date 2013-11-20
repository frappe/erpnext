# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("stock", "doctype", "item_price")

	webnotes.conn.sql("""update `tabItem Price` ip, `tabItem` i 
		set ip.item_name=i.item_name, ip.item_description=i.description 
		where ip.item_code=i.name""")

	webnotes.conn.sql("""update `tabItem Price` ip, `tabPrice List` pl 
		set ip.price_list=pl.name, ip.currency=pl.currency, 
		ip.buying_or_selling=pl.buying_or_selling 
		where ip.parent=pl.name""")

	webnotes.conn.sql("""update `tabItem Price` 
		set parent=null, parenttype=null, parentfield=null, idx=null""")
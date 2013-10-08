# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("setup", "doctype", "item_price")

	webnotes.conn.sql("""update `tabItem Price` ip, `tabItem` i 
		set ip.item_name=i.item_name, ip.description=i.description 
		where ip.item_code=i.name""")
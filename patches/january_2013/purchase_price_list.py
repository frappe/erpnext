# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("stock", "doctype", "item_price")
	
	# check for selling
	webnotes.conn.sql("""update `tabItem Price` set buying_or_selling = "Selling"
		where ifnull(buying_or_selling, '')=''""")
	
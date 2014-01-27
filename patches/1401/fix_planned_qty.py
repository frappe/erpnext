# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.conn.auto_commit_on_many_writes = 1
	from utilities.repost_stock import repost_stock
	for d in webnotes.conn.sql("""select distinct production_item, fg_warehouse 
		from `tabProduction Order` where docstatus>0""", as_dict=1):
			repost_stock(d.production_item, d.fg_warehouse)
			
	webnotes.conn.auto_commit_on_many_writes = 0
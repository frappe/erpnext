# Copyright (c) 2014, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	from utilities.repost_stock import repost_stock
	
	webnotes.conn.sql("""delete from tabBin 
		where ifnull(item_code, '') = '' or ifnull(warehouse, '')=''""")
	
	webnotes.conn.auto_commit_on_many_writes = 1
	
	for d in webnotes.conn.sql("""select item_code, warehouse, count(*) as count from tabBin 
		group by item_code, warehouse""", as_dict=1):
			if d.count > 1:
				webnotes.conn.sql("""delete from tabBin where item_code=%s 
					and warehouse=%s limit %s""", (d.item_code, d.warehouse, d.count-1))
				repost_stock(d.item_code, d.warehouse)
				
	webnotes.conn.auto_commit_on_many_writes = 0
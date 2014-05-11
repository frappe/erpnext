# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from stock.stock_ledger import update_entries_after
	webnotes.conn.auto_commit_on_many_writes = 1
	
	res = webnotes.conn.sql("""select distinct sle.item_code, sle.warehouse 
		from `tabStock Ledger Entry` sle 
		where (select has_serial_no from tabItem where name=sle.item_code)='Yes'""")
	
	for d in res:
	    try:
			update_entries_after({ "item_code": d[0], "warehouse": d[1]})
	    except:
	        pass
			
	webnotes.conn.auto_commit_on_many_writes = 0
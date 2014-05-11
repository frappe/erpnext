# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from stock.stock_ledger import update_entries_after
	
	res = webnotes.conn.sql("""select distinct item_code, warehouse from `tabStock Ledger Entry` 
		where posting_time = '00:00'""")
	
	i=0
	for d in res:
	    try:
	        update_entries_after({ "item_code": d[0], "warehouse": d[1]	})
	    except:
	        pass
	    i += 1
	    if i%20 == 0:
	        webnotes.conn.sql("commit")
	        webnotes.conn.sql("start transaction")
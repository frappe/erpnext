# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from controllers.stock_controller import update_gl_entries_after
	webnotes.conn.auto_commit_on_many_writes = 1
	
	for_items = webnotes.conn.sql_list("""select distinct sle.item_code 
		from `tabStock Ledger Entry` sle 
		where (select has_serial_no from tabItem where name=sle.item_code)='Yes'""")

	try:
		update_gl_entries_after("2013-08-01", "10:00", for_items=for_items)
	except:
		pass
			
	webnotes.conn.auto_commit_on_many_writes = 0
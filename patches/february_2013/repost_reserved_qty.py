# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	webnotes.conn.auto_commit_on_many_writes = 1
	from utilities.repost_stock import get_reserved_qty, update_bin
	
	for d in webnotes.conn.sql("select item_code, warehouse from tabBin"):
		update_bin(d[0], d[1], {
			"reserved_qty": get_reserved_qty(d[0], d[1])
		})
	webnotes.conn.auto_commit_on_many_writes = 0
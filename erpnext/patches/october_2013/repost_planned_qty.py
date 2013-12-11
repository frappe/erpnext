# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	from utilities.repost_stock import get_planned_qty, update_bin
	
	for d in webnotes.conn.sql("select item_code, warehouse from tabBin"):
		update_bin(d[0], d[1], {
			"planned_qty": get_planned_qty(d[0], d[1])
		})
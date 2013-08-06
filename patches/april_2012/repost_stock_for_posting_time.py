# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	res = webnotes.conn.sql("""select distinct item_code, warehouse from `tabStock Ledger Entry`
	 	where posting_time > '00:00:00' and posting_time < '00:01:00'""", as_dict=1)
	webnotes.conn.sql("update `tabStock Ledger Entry` set posting_time = '00:00:00' where posting_time > '00:00:00' and posting_time < '00:01:00'")

	from stock.stock_ledger import update_entries_after
	for d in res:
		update_entries_after({
			"item_code": d.item_code,
			"warehouse": d.warehouse,
		})

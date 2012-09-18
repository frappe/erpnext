from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.code import get_obj

	bins = webnotes.conn.sql("select distinct t2.name from `tabStock Ledger Entry` t1, tabBin t2 where t1.posting_time > '00:00:00' and t1.posting_time < '00:01:00' and t1.item_code = t2.item_code and t1.warehouse = t2.warehouse")
	webnotes.conn.sql("update `tabStock Ledger Entry` set posting_time = '00:00:00' where posting_time > '00:00:00' and posting_time < '00:01:00'")

	for d in bins:
		get_obj('Bin', d[0]).update_entries_after(posting_date = '2000-01-01', posting_time = '12:01')

# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import cstr
from stock.stock_ledger import update_entries_after

def execute():
	webnotes.conn.auto_commit_on_many_writes = 1
	
	pr_items = webnotes.conn.sql("""select item_code, warehouse, serial_no, valuation_rate, name 
		from `tabPurchase Receipt Item` where ifnull(serial_no, '') != '' and docstatus = 1""", 
		as_dict=True)
		
	item_warehouse = []
		
	for item in pr_items:
		serial_nos = cstr(item.serial_no).strip().split("\n")
		serial_nos = map(lambda x: x.strip(), serial_nos)

		if cstr(item.serial_no) != "\n".join(serial_nos):
			webnotes.conn.sql("""update `tabPurchase Receipt Item` set serial_no = %s 
				where name = %s""", ("\n".join(serial_nos), item.name))
			
			if [item.item_code, item.warehouse] not in item_warehouse:
				item_warehouse.append([item.item_code, item.warehouse])
		
			webnotes.conn.sql("""update `tabSerial No` set purchase_rate = %s 
				where name in (%s)""" % ('%s', ', '.join(['%s']*len(serial_nos))), 
				tuple([item.valuation_rate] + serial_nos))

	for d in item_warehouse:
		try:
			update_entries_after({"item_code": d[0], "warehouse": d[1] })
		except:
			continue
			
	webnotes.conn.auto_commit_on_many_writes = 0
# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	from webnotes.utils import flt
	bins = webnotes.conn.sql("select item_code, warehouse, name, ordered_qty from `tabBin`")
	for d in bins:
		ordered_qty = webnotes.conn.sql("""
			select sum(ifnull(po_item.qty, 0) - ifnull(po_item.received_qty, 0)) 
			from `tabPurchase Order Item` po_item, `tabPurchase Order` po
			where po_item.parent = po.name and po.docstatus = 1 and po.status != 'Stopped' 
			and po_item.item_code = %s and po_item.warehouse = %s
		""", (d[0], d[1]))

		if flt(d[3]) != flt(ordered_qty[0][0]):			
			webnotes.conn.sql("""update `tabBin` set ordered_qty = %s where name = %s""",
			 	(ordered_qty and ordered_qty[0][0] or 0, d[2]))
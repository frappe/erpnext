# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	from webnotes.utils import flt

	for d in webnotes.conn.sql("select name, item_code, warehouse, ordered_qty from tabBin", 
			as_dict=1):
		ordered_qty = webnotes.conn.sql("""
			select sum((po_item.qty - po_item.received_qty)*po_item.conversion_factor)
			from `tabPurchase Order Item` po_item, `tabPurchase Order` po
			where po_item.item_code=%s and po_item.warehouse=%s 
			and po_item.qty > po_item.received_qty and po_item.parent=po.name 
			and po.status!='Stopped' and po.docstatus=1""", (d.item_code, d.warehouse))
			
		if flt(d.ordered_qty) != flt(ordered_qty[0][0]):
			webnotes.conn.set_value("Bin", d.name, "ordered_qty", flt(ordered_qty[0][0]))
			
			webnotes.conn.sql("""update tabBin set projected_qty = actual_qty + planned_qty + 
				indented_qty + ordered_qty - reserved_qty where name = %s""", d.name)
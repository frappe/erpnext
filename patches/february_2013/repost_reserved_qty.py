# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	webnotes.conn.auto_commit_on_many_writes = 1
	repost_reserved_qty()
	webnotes.conn.auto_commit_on_many_writes = 0
	
def repost_reserved_qty():
	from webnotes.utils import flt
	bins = webnotes.conn.sql("select item_code, warehouse, name, reserved_qty from `tabBin`")
	i = 0
	for d in bins:
		i += 1
		reserved_qty = webnotes.conn.sql("""
			select 
				sum((dnpi_qty / so_item_qty) * (so_item_qty - so_item_delivered_qty))
			from 
				(
					(select
						qty as dnpi_qty,
						(
							select qty from `tabSales Order Item`
							where name = dnpi.parent_detail_docname
						) as so_item_qty,
						(
							select ifnull(delivered_qty, 0) from `tabSales Order Item`
							where name = dnpi.parent_detail_docname
						) as so_item_delivered_qty, 
						parent, name
					from 
					(
						select qty, parent_detail_docname, parent, name
						from `tabDelivery Note Packing Item` dnpi_in
						where item_code = %s and warehouse = %s
						and parenttype="Sales Order"
					and item_code != parent_item
						and exists (select * from `tabSales Order` so
						where name = dnpi_in.parent and docstatus = 1 and status != 'Stopped')
					) dnpi)
				union
					(select qty as dnpi_qty, qty as so_item_qty,
						ifnull(delivered_qty, 0) as so_item_delivered_qty, parent, name
					from `tabSales Order Item` so_item
					where item_code = %s and reserved_warehouse = %s 
					and exists(select * from `tabSales Order` so
						where so.name = so_item.parent and so.docstatus = 1 
						and so.status != 'Stopped'))
				) tab
			where 
				so_item_qty >= so_item_delivered_qty
		""", (d[0], d[1], d[0], d[1]))
		
		if flt(d[3]) != flt(reserved_qty[0][0]):
			webnotes.conn.sql("""update `tabBin` set reserved_qty = %s where name = %s""",
				(reserved_qty and reserved_qty[0][0] or 0, d[2]))
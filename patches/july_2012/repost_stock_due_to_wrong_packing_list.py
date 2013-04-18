from __future__ import unicode_literals
import webnotes
from stock.stock_ledger import update_entries_after

def execute():
	# add index
	webnotes.conn.commit()
	try:
		webnotes.conn.sql("""alter table `tabDelivery Note Packing Item`
			add index item_code_warehouse (item_code, warehouse)""")
	except:
		pass
	webnotes.conn.begin()

	webnotes.conn.auto_commit_on_many_writes = 1
	repost_reserved_qty()
	cleanup_wrong_sle()
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
					select
						qty as dnpi_qty,
						(
							select qty from `tabSales Order Item`
							where name = dnpi.parent_detail_docname
						) as so_item_qty,
						(
							select ifnull(delivered_qty, 0) from `tabSales Order Item`
							where name = dnpi.parent_detail_docname
						) as so_item_delivered_qty
					from 
					(
						select qty, parent_detail_docname
						from `tabDelivery Note Packing Item` dnpi_in
						where item_code = %s and warehouse = %s
						and parenttype="Sales Order"
						and exists (select * from `tabSales Order` so
						where name = dnpi_in.parent and docstatus = 1 and status != 'Stopped')
					) dnpi
				) tab 
			where 
				so_item_qty >= so_item_delivered_qty
		""", (d[0], d[1]))

		if flt(d[3]) != flt(reserved_qty[0][0]):
			webnotes.conn.sql("""
				update `tabBin` set reserved_qty = %s where name = %s
			""", (reserved_qty and reserved_qty[0][0] or 0, d[2]))
		
def cleanup_wrong_sle():
	sle = webnotes.conn.sql("""
		select item_code, warehouse, voucher_no, name
		from `tabStock Ledger Entry` sle
		where voucher_type = 'Delivery Note'
		and not exists(
			select name from `tabDelivery Note Packing Item` 
			where item_code = sle.item_code 
			and qty = abs(sle.actual_qty)
			and parent = sle.voucher_no
		) and not exists (
			select name from `tabDelivery Note Item` 
			where item_code = sle.item_code 
			and qty = abs(sle.actual_qty)
			and parent = sle.voucher_no
		)
	""")
	if sle:
		for d in sle:
			webnotes.conn.sql("update `tabStock Ledger Entry` set is_cancelled = 'Yes' where name = %s", d[3])
			create_comment(d[3])
			update_entries_after({
				"item_code": d[0],
				"warehouse": d[1],
				"posting_date": "2012-07-01",
				"posting_time": "12:05"
			})
			
def create_comment(dn):
	from webnotes.model.doc import Document
	cmt = Document('Comment')
	cmt.comment = 'Cancelled by administrator due to wrong entry in packing list'
	cmt.comment_by = 'Administrator'
	cmt.comment_by_fullname = 'Administrator'
	cmt.comment_doctype = 'Stock Ledger Entry'
	cmt.comment_docname = dn
	cmt.save(1)
	
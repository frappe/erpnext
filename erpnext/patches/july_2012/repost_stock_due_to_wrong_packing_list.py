def repost_reserved_qty():
	import webnotes
	from webnotes.utils import flt
	bins = webnotes.conn.sql("select item_code, warehouse, name, reserved_qty from `tabBin`")
	for d in bins:
		reserved_qty = webnotes.conn.sql("""
			select sum((dnpi.qty/so_item.qty)*(so_item.qty - ifnull(so_item.delivered_qty, 0))) 
			
			from `tabDelivery Note Packing Item` dnpi, `tabSales Order Item` so_item, `tabSales Order` so
			
			where dnpi.item_code = %s
			and dnpi.warehouse = %s
			and dnpi.parent = so.name
			and so_item.parent = so.name
			and dnpi.parenttype = 'Sales Order'
			and dnpi.parent_detail_docname = so_item.name
			and dnpi.parent_item = so_item.item_code
			and so.docstatus = 1
			and so.status != 'Stopped'
		""", (d[0], d[1]))
		if flt(d[3]) != flt(reserved_qty[0][0]):
			print d[3], reserved_qty[0][0]
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
		print sle
		for d in sle:
			webnotes.conn.sql("update `tabStock Ledger Entry` set is_cancelled = 'Yes' where name = %s", d[3])
			create_comment(d[3])
			repost_bin(d[0], d[1])
	
def create_comment(dn):
	from webnotes.model.doc import Document
	cmt = Document('Comment')
	for arg in ['comment', 'comment_by', 'comment_by_fullname', 'comment_doctype', \
		'comment_docname']:
		cmt.fields[arg] = args[arg]
	cmt.comment = 'Cancelled by administrator due to wrong entry in packing list'
	cmt.comment_by = 'Administrator'
	cmt.comment_by_fullname = 'Administrator'
	cmt.comment_doctype = 'Stock Ledger Entry'
	cmt.comment_docname = dn
	cmt.save(1)
	
	
def repost_bin(item, wh):
	from webnotes.model.code import get_obj	
	bin = webnotes.conn.sql("select name from `tabBin` \
		where item_code = %s and warehouse = %s", (item, wh))
			
	get_obj('Bin', bin[0][0]).update_entries_after(posting_date = '2012-07-01', posting_time = '12:05')
	
	
def execute():
	repost_reserved_qty()
	cleanup_wrong_sle()

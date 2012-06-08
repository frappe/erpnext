def execute():
	import webnotes
	webnotes.conn.sql("update `tabPurchase Invoice Item` t1, `tabPurchase Order Item` t2 set t1.uom = t2.uom where ifnull(t1.po_detail, '') != '' and t1.po_detail = t2.name")
	webnotes.conn.sql("update `tabPurchase Invoice Item` t1, `tabPurchase Receipt Item` t2 set t1.uom = t2.uom where ifnull(t1.pr_detail, '') != '' and t1.pr_detail = t2.name")
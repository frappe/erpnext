def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	sql = webnotes.conn.sql
	
	# Reload item table
	reload_doc('accounts', 'doctype', 'pv_detail')
	reload_doc('buying', 'doctype', 'po_detail')
	reload_doc('stock', 'doctype', 'purchase_receipt_detail')
	
	# copy project value from parent to child
	sql("update `tabPO Detail` t1, `tabPurchase Order` t2 set t1.project_name = t2.project_name where t1.parent = t2.name and ifnull(t1.project_name, '') = ''")
	sql("update `tabPV Detail` t1, `tabPayable Voucher` t2 set t1.project_name = t2.project_name where t1.parent = t2.name and ifnull(t1.project_name, '') = ''")
	sql("update `tabPurchase Receipt Detail` t1, `tabPurchase Receipt` t2 set t1.project_name = t2.project_name where t1.parent = t2.name and ifnull(t1.project_name, '') = ''")
	
	# delete project from parent
	sql("delete from `tabDocField` where fieldname = 'project_name' and parent in ('Purchase Order', 'Purchase Receipt', 'Payable Voucher')")


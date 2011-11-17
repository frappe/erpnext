def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc

	reload_doc('stock', 'doctype', 'landed_cost_wizard')
	reload_doc('stock', 'doctype', 'lc_pr_detail')
	
	sql("delete from `tabDocField` where parent ='LC PR Detail' and fieldname in ('purchase_receipt_no', 'include_in_landed_cost')")

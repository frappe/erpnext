def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	
	# reload jv gl mapper
	reload_doc('accounts', 'GL Mapper', 'Journal Voucher')

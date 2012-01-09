def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	from webnotes.model.code import get_obj

	reload_doc('accounts', 'doctype', 'receivable_voucher')

	reload_doc('setup', 'doctype', 'features_setup')
	get_obj('Features setup').validate()

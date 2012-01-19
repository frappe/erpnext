def execute():
	"""
		Remove One Get TDS button, which is appearing twice in JV
	"""
	import webnotes
	webnotes.conn.sql("""
		DELETE from `tabDocField`
		WHERE parent='Journal Voucher'
		AND label='Get TDS'
		AND fieldtype='Button'
	""")

	from webnotes.modules.module_manager import reload_doc
	reload_doc('accounts', 'doctype', 'journal_voucher')

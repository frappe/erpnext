def execute():
	"""
		Changes allocated_to option to Profile in
		DocType Customer Issue
	"""
	import webnotes
	webnotes.conn.sql("""
		UPDATE `tabDocField`
		SET options='Profile'
		WHERE fieldname='allocated_to'
	""")

	from webnotes.modules.module_manager import reload_doc
	reload_doc('support', 'doctype', 'customer_issue')

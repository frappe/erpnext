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

	webnotes.conn.sql("""
		DELETE from `tabDocField`
		WHERE parent='Customer Issue'
		AND label='Make Maintenance Visit'
	""")

	from webnotes.modules.module_manager import reload_doc
	reload_doc('support', 'doctype', 'customer_issue')

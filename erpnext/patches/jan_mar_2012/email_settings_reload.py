def execute():
	"""
		* Change type of mail_port field to int
		* reload email settings
	"""
	import webnotes
	webnotes.conn.sql("""
		UPDATE `tabDocField` SET fieldtype='Int'
		WHERE parent = 'Email Settings' AND fieldname = 'mail_port'
	""")

	from webnotes.modules.module_manager import reload_doc
	reload_doc('setup', 'doctype', 'email_settings')

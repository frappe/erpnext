import webnotes
def execute():
	"""
		* Change option of doclayer's doc_type field
		* Reload doclayer
	"""
	webnotes.conn.sql("""
		UPDATE `tabDocField` SET options=NULL
		WHERE parent='DocLayer' AND fieldname='doc_type'
	""")
	from webnotes.modules.module_manager import reload_doc
	reload_doc('core', 'doctype', 'doclayer')

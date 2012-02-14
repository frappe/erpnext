def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('website', 'doctype', 'website_settings')

	res = webnotes.conn.sql("""\
		SELECT name FROM `tabDocPerm`
		WHERE parent='Website Settings' AND role='All' AND permlevel=1""")
	if not res:
		idx = webnotes.conn.sql("""\
			SELECT MAX(idx) FROM `tabDocPerm`
			WHERE parent='Website Settings'
			""")[0][0]
		from webnotes.model.doc import Document
		d = Document('DocType', 'Website Settings')
		perm = d.addchild('permissions', 'DocPerm')
		perm.read = 1
		perm.role = 'All'
		perm.permlevel = 1
		perm.idx = idx + 1
		perm.save()


def execute():
	import webnotes
	sql = webnotes.conn.sql
	from webnotes.model import delete_doc

	del_rec = {
		'DocType'	:	['Update Series', 'File', 'File Browser Control', 'File Group', 'Tag Detail', 'DocType Property Setter', 'Company Group'],
		'Page'		:	['File Browser']
	}

	for d in del_rec:
		for r in del_rec[d]:
			delete_doc(d, r)

	sql("delete from tabDocField where label='Repair Indent' and parent = 'Indent'")

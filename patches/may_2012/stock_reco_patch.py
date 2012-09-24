from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('stock', 'doctype', 'stock_reconciliation')

	sr = webnotes.conn.sql("select name, file_list from `tabStock Reconciliation` where docstatus = 1")
	for d in sr:
		if d[1]:
			filename = d[1].split(',')[1]
		
			from webnotes.utils import file_manager
			fn, content = file_manager.get_file(filename)
		
			if not isinstance(content, basestring) and hasattr(content, 'tostring'):
				content = content.tostring()

			webnotes.conn.sql("update `tabStock Reconciliation` set diff_info = %s where name = %s and ifnull(diff_info, '') = ''", (content, d[0]))

from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.code import get_obj
	fs = get_obj('Features Setup')
	fs.doc.fs_item_barcode = 0
	fs.doc.save()
	fs.validate()
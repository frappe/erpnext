# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.code import get_obj
	fs = get_obj('Features Setup')
	fs.doc.fs_item_barcode = 0
	fs.doc.save()
	fs.validate()
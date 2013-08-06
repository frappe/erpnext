# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model import delete_doc
	webnotes.conn.sql("update `tabDocType` set module = 'Utilities' where name in ('Question', 'Answer')")
	delete_doc('Module Def', 'Knowledge Base')

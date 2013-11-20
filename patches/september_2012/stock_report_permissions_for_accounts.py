# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.doc import addchild
	from webnotes.model.code import get_obj
	
	for parent in ("Stock Ledger Entry", "Bin"):
		existing = webnotes.conn.sql("""select role from `tabDocPerm`
			where permlevel=0 and parent=%s""", (parent,))
	
		if "Accounts Manager" not in map(lambda x: x[0], existing):
			doctype_obj = get_obj("DocType", parent, with_children=1)
			ch = addchild(doctype_obj.doc, "permissions", "DocPerm")
			ch.permlevel = 0
			ch.role = "Accounts Manager"
			ch.read = 1
			ch.save()
		
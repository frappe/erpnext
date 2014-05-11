# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.doc import addchild
	from webnotes.model.code import get_obj
	
	existing = webnotes.conn.sql("""select role, name from `tabDocPerm`
		where permlevel=0 and parent='Communication'""")

	for role in ("Support Manager", "System Manager"):
		if role not in map(lambda x: x[0], existing):
			doctype_obj = get_obj("DocType", "Communication", with_children=1)
			ch = addchild(doctype_obj.doc, "permissions", "DocPerm")
			ch.permlevel = 0
			ch.role = role
			ch.read = 1
			ch.write = 1
			ch.create = 1
			ch.cancel = 1
			ch.save()
		else:
			webnotes.conn.set_value("DocPerm", dict(existing).get(role), "cancel", 1)

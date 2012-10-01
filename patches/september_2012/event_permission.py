from __future__ import unicode_literals
import webnotes
from webnotes.model.code import get_obj
from webnotes.model.doc import addchild

def execute():
	existing = webnotes.conn.sql("""select name from `tabDocPerm`
		where permlevel=0 and parent='Event' and role='System Manager'
		and cancel=1""")
	if not existing:
		ev_obj = get_obj("DocType", "Event", with_children=1)
		ch = addchild(ev_obj.doc, "permissions", "DocPerm")
		ch.permlevel = 0
		ch.role = 'System Manager'
		ch.read = ch.write = ch.create = ch.cancel = 1
		ch.save()
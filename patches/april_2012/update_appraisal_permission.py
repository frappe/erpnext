from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.doc import addchild
	from webnotes.model.code import get_obj
	
	webnotes.conn.sql("delete from `tabDocPerm` where role = 'All' and permlevel = 0 and parent in ('Appraisal', 'Ticket', 'Project')")

	appr = get_obj('DocType', 'Appraisal', with_children=1)
	ch = addchild(appr.doc, 'permissions', 'DocPerm')
	ch.permlevel = 0
	ch.role = 'Employee'
	ch.read = 1
	ch.write = 1
	ch.save()

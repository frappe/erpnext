# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("""
		delete from `tabDocPerm`
		where 
			role in ('Sales User', 'Sales Manager', 'Sales Master Manager', 
				'Purchase User', 'Purchase Manager', 'Purchase Master Manager')
			and parent = 'Sales and Purchase Return Tool'
	""")
	
	webnotes.conn.sql("""delete from `tabDocPerm` where ifnull(role, '') = ''""")
	
	if not webnotes.conn.sql("""select name from `tabDocPerm` where parent = 'Leave Application'
			and role = 'Employee' and permlevel = 1"""):
		from webnotes.model.code import get_obj
		from webnotes.model.doc import addchild
		leave_app = get_obj('DocType', 'Leave Application', with_children=1)
		ch = addchild(leave_app.doc, 'permissions', 'DocPerm')
		ch.role = 'Employee'
		ch.permlevel = 1
		ch.read = 1
		ch.save()
# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.doc import addchild
	from webnotes.model.code import get_obj

	webnotes.conn.sql("delete from `tabDocPerm` where role = 'All' and parent = 'Address'")

	role1 = ['Sales User', 'Purchase User', 'Accounts User', 'Maintenance User']
	role2 = ['Sales Manager', 'Sales Master Manager', 'Purchase Manager', 'Purchase Master Manager', 'Accounts Manager', 'Maintenance Manager']

	addr = get_obj('DocType', 'Address', with_children=1)
	for d in role1+role2:
		ch = addchild(addr.doc, 'permissions', 'DocPerm')
		ch.role = d
		ch.read = 1
		ch.write = 1
		ch.create = 1
		if d in role2:
			ch.cancel = 1

		ch.save()

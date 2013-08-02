# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	"""Make profile readonly for role All"""
	import webnotes.model.doc
	webnotes.conn.sql("delete from `tabDocPerm` where parent='Profile' and role='All'")
	new_perms = [
		{
			'parent': 'Profile',
			'parentfield': 'permissions',
			'parenttype': 'DocType',
			'role': 'All',			
			'permlevel': 0,
			'read': 1,
		},
	]
	for perms in new_perms:
		doc = webnotes.model.doc.Document('DocPerm')
		doc.fields.update(perms)
		doc.save()
	webnotes.conn.commit()
	webnotes.conn.begin()
	webnotes.reload_doc('core', 'doctype', 'profile')
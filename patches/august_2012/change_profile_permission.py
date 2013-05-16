from __future__ import unicode_literals
def execute():
	import webnotes
	import webnotes.model.doc
	webnotes.conn.sql("delete from `tabDocPerm` where parent='Profile' and permlevel=1")
	new_perms = [
		{
			'parent': 'Profile',
			'parentfield': 'permissions',
			'parenttype': 'DocType',
			'role': 'Administrator',			
			'permlevel': 1,
			'read': 1,
			'write': 1
		},
		{
			'parent': 'Profile',
			'parentfield': 'permissions',
			'parenttype': 'DocType',
			'role': 'System Manager',
			'permlevel': 1,
			'read': 1,
			'write': 1
		},
		
	]
	for perms in new_perms:
		doc = webnotes.model.doc.Document('DocPerm')
		doc.fields.update(perms)
		doc.save()
	webnotes.conn.commit()
	webnotes.conn.begin()
	
	webnotes.reload_doc('core', 'doctype', 'profile')
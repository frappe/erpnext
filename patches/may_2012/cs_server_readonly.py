from __future__ import unicode_literals
def execute():
	"""Make server custom script readonly for system manager"""
	import webnotes.model.doc
	new_perms = [
		{
			'parent': 'Custom Script',
			'parentfield': 'permissions',
			'parenttype': 'DocType',
			'role': 'System Manager',			
			'permlevel': 1,
			'read': 1,
		},
		{
			'parent': 'Custom Script',
			'parentfield': 'permissions',
			'parenttype': 'DocType',
			'role': 'Administrator',			
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
	webnotes.reload_doc('core', 'doctype', 'custom_script')
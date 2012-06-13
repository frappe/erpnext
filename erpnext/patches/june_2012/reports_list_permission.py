def execute():
	"""allow read permission to all for report list"""
	import webnotes
	import webnotes.model.doc
	new_perms = [
		{
			'parent': 'Report',
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
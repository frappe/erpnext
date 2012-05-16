def execute():
	"""Make standard print formats readonly for system manager"""
	import webnotes.model.doc
	new_perms = [
		{
			'parent': 'Print Format',
			'parentfield': 'permissions',
			'parenttype': 'DocType',
			'role': 'System Manager',			
			'permlevel': 1,
			'read': 1,
		},
		{
			'parent': 'Print Format',
			'parentfield': 'permissions',
			'parenttype': 'DocType',
			'role': 'Administrator',			
			'permlevel': 1,
			'read': 1,
			'write': 1
		},
	]
	import webnotes.model.sync
	webnotes.model.sync.sync('core', 'print_format')
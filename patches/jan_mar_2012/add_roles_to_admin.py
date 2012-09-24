from __future__ import unicode_literals
def execute():
	"""
		Adds various roles to Administrator. This patch is for making master db
		ready for on premise installation
	"""
	import webnotes
	from webnotes.model.code import get_obj
	from webnotes.model.doc import Document
	sc = get_obj('Setup Control', 'Setup Control')
	sc.add_roles(Document('Profile', 'Administrator'))

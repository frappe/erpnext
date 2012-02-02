class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		"""clear cache"""
		# set home page
		import webnotes
		from webnotes.model.doc import Document
		
		webnotes.conn.sql("""delete from `tabDefault Home Page` where role='Guest'""")
		
		d = Document('Default Home Page')
		d.parent = 'Control Panel'
		d.role = 'Guest'
		d.home_page = self.doc.home_page
		d.save()
		
		from webnotes.session_cache import clear_cache
		clear_cache('Guest')
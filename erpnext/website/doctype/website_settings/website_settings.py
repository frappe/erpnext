class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		"""
			* set home page
			* validate domain list
			* clear cache
		"""
		self.set_home_page()

		self.validate_domain_list()	
		
		from webnotes.session_cache import clear_cache
		clear_cache('Guest')

	
	def set_home_page(self):

		import webnotes
		from webnotes.model.doc import Document
		
		webnotes.conn.sql("""delete from `tabDefault Home Page` where role='Guest'""")
		
		d = Document('Default Home Page')
		d.parent = 'Control Panel'
		d.role = 'Guest'
		d.home_page = self.doc.home_page
		d.save()

	
	def validate_domain_list(self):
		"""
			Validate domain list if SaaS
		"""
		import webnotes

		try:
			from server_tools.gateway_utils import validate_domain_list
			res = validate_domain_list(self.doc.domain_list, webnotes.conn.cur_db_name)
			if not res:
				webnotes.msgprint("""\
					There was some error in validating the domain list.
					Please contact us at support@erpnext.com""", raise_exception=1)				
		except ImportError, e:
			pass

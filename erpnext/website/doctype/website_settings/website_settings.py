# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

	def on_update(self):
		# make js and css
		from webnotes.cms.make import make_web_core
		make_web_core()
		
		# clear web cache
		import website.web_cache
		#website.web_cache.refresh_cache(build=['Blog'])
		website.web_cache.refresh_cache()

		from webnotes.session_cache import clear_cache
		clear_cache('Guest')

	def set_home_page(self):

		import webnotes
		from webnotes.model.doc import Document
		
		webnotes.conn.sql("""delete from `tabDefault Home Page` where role='Guest'""")
		
		d = Document('Default Home Page')
		d.parent = 'Control Panel'
		d.parenttype = 'Control Panel'
		d.parentfield = 'default_home_pages'
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

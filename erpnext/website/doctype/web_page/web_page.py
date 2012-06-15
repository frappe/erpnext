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

import webnotes
import website.utils

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	def autoname(self):
		"""name from title"""
		self.doc.name = website.utils.page_name(self.doc.title)

	def validate(self):
		"""make page for this product"""
		from jinja2 import Template
		import os

		# we need the name for the templates
		if self.doc.name.startswith('New Web Page'):
			self.autoname()

		# page name updates with the title
		self.doc.page_name = website.utils.page_name(self.doc.title)
		
		# markdown
		website.utils.markdown(self.doc, ['head_section','main_section', 'side_section'])
		
		# make page layout
		with open(os.path.join(os.path.dirname(__file__), 'template.html'), 'r') as f:
			self.doc.content = Template(f.read()).render(doc=self.doc)
		
		self.cleanup_temp()
		self.if_home_clear_cache()
				
	def cleanup_temp(self):
		"""cleanup temp fields"""
		fl = ['main_section_html', 'side_section_html', \
			'head_section_html']
		for f in fl:
			if f in self.doc.fields:
				del self.doc.fields[f]
				
	def if_home_clear_cache(self):
		"""if home page, clear cache"""
		if webnotes.conn.get_value("Website Settings", None, "home_page")==self.doc.name:
			from webnotes.session_cache import clear_cache
			clear_cache('Guest')			
	
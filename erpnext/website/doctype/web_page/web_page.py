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

	def on_update(self):
		"""make page for this product"""
		from jinja2 import Template
		from webnotes.utils import global_date_format
		from webnotes.model.code import get_obj
		import os

		# we need the name for the templates
		if self.doc.name.startswith('New Web Page'):
			self.autoname()

		if self.doc.page_name:
			webnotes.conn.sql("""delete from tabPage where name=%s""", self.doc.page_name)

		p = website.utils.add_page(self.doc.name)
		self.doc.page_name = p.name
		
		self.doc.updated = global_date_format(self.doc.modified)
		website.utils.markdown(self.doc, ['head_section','main_section', 'side_section'])
				
		with open(os.path.join(os.path.dirname(__file__), 'template.html'), 'r') as f:
			p.content = Template(f.read()).render(doc=self.doc)

		p.title = self.doc.title
		p.web_page = 'Yes'
		
		if self.doc.insert_code:
			p.script = self.doc.javascript

		if self.doc.insert_style:
			p.style = self.doc.css

		p.save()
		get_obj(doc=p).write_cms_page()
		
		website.utils.add_guest_access_to_page(p.name)
		self.cleanup_temp()

		self.doc.save()

		self.if_home_clear_cache()
			
	def add_page_links(self):
		"""add links for next_page and see_also"""
		if self.doc.next_page:
			self.doc.next_page_html = """<div class="info-box round" style="text-align: right">
				<b>Next:</b>
				<a href="#!%(name)s">%(title)s</a></div>""" % {"name":self.doc.next_page, \
						"title": webnotes.conn.get_value("Page", self.doc.next_page, "title")}

		self.doc.see_also = ''
		for d in self.doclist:
			if d.doctype=='Related Page':
				tmp = {"page":d.page, "title":webnotes.conn.get_value('Page', d.page, 'title')}
				self.doc.see_also += """<div><a href="#!%(page)s">%(title)s</a></div>""" % tmp
				
	def cleanup_temp(self):
		"""cleanup temp fields"""
		fl = ['main_section_html', 'side_section_html', 'see_also', \
			'next_page_html', 'head_section_html', 'updated']
		for f in fl:
			if f in self.doc.fields:
				del self.doc.fields[f]
				
	def if_home_clear_cache(self):
		"""if home page, clear cache"""
		if webnotes.conn.get_value("Website Settings", None, "home_page")==self.doc.name:
			from webnotes.session_cache import clear_cache
			clear_cache('Guest')			
	
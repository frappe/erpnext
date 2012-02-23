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

"""
record of files

naming for same name files: file.gif, file-1.gif, file-2.gif etc
"""

import webnotes
import website.utils

class DocType():
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def autoname(self):
		"""save file by its name"""
		self.doc.name = website.utils.page_name(self.doc.title)
	
	def validate(self):
		"""write/update 'Page' with the blog"""		
		p = website.utils.add_page(self.doc.title)
		self.doc.name = p.name
		
		from jinja2 import Template
		import markdown2
		import os
		from webnotes.utils import global_date_format, get_full_name
		
		self.doc.content_html = markdown2.markdown(self.doc.content or '')
		self.doc.full_name = get_full_name(self.doc.owner)
		self.doc.updated = global_date_format(self.doc.modified)
		
		with open(os.path.join(os.path.dirname(__file__), 'template.html'), 'r') as f:
			p.content = Template(f.read()).render(doc=self.doc)
		
		with open(os.path.join(os.path.dirname(__file__), 'blog_page.js'), 'r') as f:
			p.script = Template(f.read()).render(doc=self.doc)
				
		p.save()
		
		website.utils.add_guest_access_to_page(p.name)
		
		# cleanup
		for f in ['content_html', 'full_name', 'updated']:
			if f in self.doc.fields:
				del self.doc.fields[f]
				

			
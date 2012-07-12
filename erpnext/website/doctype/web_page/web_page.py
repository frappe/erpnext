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
import website.web_page

class DocType(website.web_page.Page):
	def __init__(self, d, dl):
		super(DocType, self).__init__('Web Page')
		self.doc, self.doclist = d, dl

	def on_update(self):
		super(DocType, self).on_update()
		self.if_home_clear_cache()

	def if_home_clear_cache(self):
		"""if home page, clear cache"""
		if webnotes.conn.get_value("Website Settings", None, "home_page")==self.doc.name:
			from webnotes.session_cache import clear_cache
			clear_cache('Guest')
			import website.web_cache
			website.web_cache.clear_cache(self.doc.page_name)
			website.web_cache.clear_cache('index')
			
	def prepare_template_args(self):
		self.markdown_to_html(['head_section','main_section', 'side_section'])
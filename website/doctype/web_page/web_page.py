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

from __future__ import unicode_literals
import webnotes

class DocType():
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def autoname(self):
		from webnotes.webutils import page_name
		self.doc.name = page_name(self.doc.title)

	def on_update(self):
		from webnotes.webutils import update_page_name
		update_page_name(self.doc, self.doc.title)
		self.if_home_clear_cache()

	def if_home_clear_cache(self):
		"""if home page, clear cache"""
		if webnotes.conn.get_value("Website Settings", None, "home_page")==self.doc.name:
			from webnotes.sessions import clear_cache
			clear_cache('Guest')
			
			from webnotes.webutils import clear_cache
			clear_cache(self.doc.page_name)
			clear_cache('index')
			
	def prepare_template_args(self):
		if self.doc.slideshow:
			from website.helpers.slideshow import get_slideshow
			get_slideshow(self)

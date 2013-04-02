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
class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		self.set_home_page()

	def on_update(self):
		# make js and css
		from website.helpers.make_web_include_files import make
		make()
		
		# clear web cache (for menus!)
		from webnotes.webutils import clear_cache
		clear_cache()

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
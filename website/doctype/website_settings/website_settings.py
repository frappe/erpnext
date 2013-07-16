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
from webnotes import _, msgprint

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		self.set_home_page()
		self.validate_top_bar_items()
		self.validate_footer_items()
			
	def validate_top_bar_items(self):
		"""validate url in top bar items"""
		for top_bar_item in self.doclist.get({"parentfield": "top_bar_items"}):
			if top_bar_item.parent_label:
				parent_label_item = self.doclist.get({"parentfield": "top_bar_items", 
					"label": top_bar_item.parent_label})
				
				if not parent_label_item:
					# invalid item
					msgprint(_(self.meta.get_label("parent_label", parentfield="top_bar_items")) +
						(" \"%s\": " % top_bar_item.parent_label) + _("does not exist"), raise_exception=True)
				
				elif not parent_label_item[0] or parent_label_item[0].url:
					# parent cannot have url
					msgprint(_("Top Bar Item") + (" \"%s\": " % top_bar_item.parent_label) +
						_("cannot have a URL, because it has child item(s)"), raise_exception=True)
	
	def validate_footer_items(self):
		"""clear parent label in footer"""
		for footer_item in self.doclist.get({"parentfield": "footer_items"}):
			footer_item.parent_label = None

	def on_update(self):
		# make js and css
		from website.helpers.make_web_include_files import make
		make()
		
		# clear web cache (for menus!)
		from webnotes.webutils import clear_cache
		clear_cache()

	def set_home_page(self):
		from webnotes.model.doc import Document
		webnotes.conn.sql("""delete from `tabDefault Home Page` where role='Guest'""")
		
		d = Document('Default Home Page')
		d.parent = 'Control Panel'
		d.parenttype = 'Control Panel'
		d.parentfield = 'default_home_pages'
		d.role = 'Guest'
		d.home_page = self.doc.home_page
		d.save()
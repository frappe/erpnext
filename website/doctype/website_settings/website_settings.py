# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

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
		
	def make_website(self):
		# set item pages
		for name in webnotes.conn.sql_list("""select name from tabItem where 
			ifnull(show_in_website, 0)=0 and is_sales_item ='Yes' """):
			webnotes.msgprint("Setting 'Show in Website' for:" + name)
			item = webnotes.bean("Item", name)
			item.doc.show_in_website = 1
			item.doc.website_warehouse = item.doc.default_warehouse
			item.doc.website_image = item.doc.image
			item.save()
		
		# set item group pages
		for name in webnotes.conn.sql_list("""select name from `tabItem Group` where 
			ifnull(show_in_website, 0)=0 and exists (select name from tabItem where 
				ifnull(show_in_website, 0)=1)"""):
			webnotes.msgprint("Setting 'Show in Website' for:" + name)
			item_group = webnotes.bean("Item Group", name)
			item_group.doc.show_in_website = 1
			item_group.save()
			
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
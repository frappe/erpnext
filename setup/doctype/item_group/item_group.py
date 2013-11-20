# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils.nestedset import DocTypeNestedSet
from webnotes.webutils import WebsiteGenerator

class DocType(DocTypeNestedSet, WebsiteGenerator):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.nsm_parent_field = 'parent_item_group'
		
	def on_update(self):
		DocTypeNestedSet.on_update(self)
		WebsiteGenerator.on_update(self)
		
		self.validate_name_with_item()
		
		from selling.utils.product import invalidate_cache_for
		invalidate_cache_for(self.doc.name)
				
		self.validate_one_root()
		
	def validate_name_with_item(self):
		if webnotes.conn.exists("Item", self.doc.name):
			webnotes.msgprint("An item exists with same name (%s), please change the \
				item group name or rename the item" % self.doc.name, raise_exception=1)
		
	def get_context(self):
		from selling.utils.product import get_product_list_for_group, \
			get_parent_item_groups, get_group_item_count

		self.doc.sub_groups = webnotes.conn.sql("""select name, page_name
			from `tabItem Group` where parent_item_group=%s
			and ifnull(show_in_website,0)=1""", self.doc.name, as_dict=1)

		for d in self.doc.sub_groups:
			d.count = get_group_item_count(d.name)
			
		self.doc.items = get_product_list_for_group(product_group = self.doc.name, limit=100)
		self.parent_groups = get_parent_item_groups(self.doc.name)
		self.doc.title = self.doc.name

		if self.doc.slideshow:
			from website.doctype.website_slideshow.website_slideshow import get_slideshow
			get_slideshow(self)
		
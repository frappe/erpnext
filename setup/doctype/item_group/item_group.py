# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes


from webnotes.utils.nestedset import DocTypeNestedSet

class DocType(DocTypeNestedSet):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.nsm_parent_field = 'parent_item_group'
		
	def on_update(self):
		super(DocType, self).on_update()
		
		self.validate_name_with_item()
		
		from website.helpers.product import invalidate_cache_for
		
		if self.doc.show_in_website:
			from webnotes.webutils import update_page_name
			# webpage updates
			page_name = self.doc.name
			update_page_name(self.doc, page_name)
			invalidate_cache_for(self.doc.name)

		elif self.doc.page_name:
			# if unchecked show in website
			
			from webnotes.webutils import delete_page_cache
			delete_page_cache(self.doc.page_name)
			
			invalidate_cache_for(self.doc.name)
			
			webnotes.conn.set(self.doc, "page_name", None)
		
		self.validate_one_root()
		
	def validate_name_with_item(self):
		if webnotes.conn.exists("Item", self.doc.name):
			webnotes.msgprint("An item exists with same name (%s), please change the \
				item group name or rename the item" % self.doc.name, raise_exception=1)
	
	def prepare_template_args(self):
		from website.helpers.product import get_product_list_for_group, \
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
			from website.helpers.slideshow import get_slideshow
			get_slideshow(self)
		
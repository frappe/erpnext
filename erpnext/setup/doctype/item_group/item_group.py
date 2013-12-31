# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils.nestedset import DocTypeNestedSet
from webnotes.webutils import WebsiteGenerator
from webnotes.webutils import delete_page_cache

class DocType(DocTypeNestedSet, WebsiteGenerator):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.nsm_parent_field = 'parent_item_group'
		
	def on_update(self):
		DocTypeNestedSet.on_update(self)
		WebsiteGenerator.on_update(self)
		
		self.validate_name_with_item()
		
		invalidate_cache_for(self.doc.name)
				
		self.validate_one_root()
		
	def validate_name_with_item(self):
		if webnotes.conn.exists("Item", self.doc.name):
			webnotes.msgprint("An item exists with same name (%s), please change the \
				item group name or rename the item" % self.doc.name, raise_exception=1)
		
def get_group_item_count(item_group):
	child_groups = ", ".join(['"' + i[0] + '"' for i in get_child_groups(item_group)])
	return webnotes.conn.sql("""select count(*) from `tabItem` 
		where docstatus = 0 and show_in_website = 1
		and (item_group in (%s)
			or name in (select parent from `tabWebsite Item Group` 
				where item_group in (%s))) """ % (child_groups, child_groups))[0][0]

def get_parent_item_groups(item_group_name):
	item_group = webnotes.doc("Item Group", item_group_name)
	return webnotes.conn.sql("""select name, page_name from `tabItem Group`
		where lft <= %s and rgt >= %s 
		and ifnull(show_in_website,0)=1
		order by lft asc""", (item_group.lft, item_group.rgt), as_dict=True)
		
def invalidate_cache_for(item_group):
	for i in get_parent_item_groups(item_group):
		if i.page_name:
			delete_page_cache(i.page_name)

# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils.nestedset import NestedSet
from frappe.website.website_generator import WebsiteGenerator
from frappe.website.render import clear_cache

class ItemGroup(NestedSet, WebsiteGenerator):
	nsm_parent_field = 'parent_item_group'

	def autoname(self):
		self.name = self.item_group_name

	def validate(self):
		if not self.parent_website_route:
			self.parent_website_route = frappe.get_website_route("Item Group",
				self.parent_item_group)

	def on_update(self):
		NestedSet.on_update(self)
		WebsiteGenerator.on_update(self)
		invalidate_cache_for(self)
		self.validate_name_with_item()
		self.validate_one_root()

	def after_rename(self, olddn, newdn, merge=False):
		NestedSet.after_rename(self, olddn, newdn, merge)
		WebsiteGenerator.after_rename(self, olddn, newdn, merge)

	def on_trash(self):
		NestedSet.on_trash(self)
		WebsiteGenerator.on_trash(self)

	def validate_name_with_item(self):
		if frappe.db.exists("Item", self.name):
			frappe.throw(frappe._("An item exists with same name ({0}), please change the item group name or rename the item").format(self.name))

def get_parent_item_groups(item_group_name):
	item_group = frappe.get_doc("Item Group", item_group_name)
	return frappe.db.sql("""select name, page_name from `tabItem Group`
		where lft <= %s and rgt >= %s
		and ifnull(show_in_website,0)=1
		order by lft asc""", (item_group.lft, item_group.rgt), as_dict=True)

def invalidate_cache_for(doc, item_group=None):
	if not item_group:
		item_group = doc.name

	for i in get_parent_item_groups(item_group):
		if i.page_name:
			clear_cache(i.page_name)

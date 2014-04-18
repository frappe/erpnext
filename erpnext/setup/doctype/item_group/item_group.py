# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils.nestedset import NestedSet
from frappe.website.website_generator import WebsiteGenerator

class ItemGroup(NestedSet, WebsiteGenerator):
	nsm_parent_field = 'parent_item_group'

	def autoname(self):
		self.name = self.item_group_name

	def validate(self):
		if not self.parent_website_route:
			self.parent_website_route = frappe.get_website_route("Item Group",
				self.parent_item_group)

	def on_update(self):
		super(ItemGroup, self).on_update()
		self.validate_name_with_item()
		self.validate_one_root()

	def after_rename(self, olddn, newdn, merge=False):
		super(ItemGroup, self).on_update()

	def on_trash(self):
		super(ItemGroup, self).on_update()

	def validate_name_with_item(self):
		if frappe.db.exists("Item", self.name):
			frappe.throw(frappe._("An item exists with same name ({0}), please change the item group name or rename the item").format(self.name))

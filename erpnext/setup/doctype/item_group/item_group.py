# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils.nestedset import DocTypeNestedSet

class ItemGroup(DocTypeNestedSet):
		self.nsm_parent_field = 'parent_item_group'
	
	def validate(self):
		if not self.doc.parent_website_route:
			self.doc.parent_website_route = frappe.get_website_route("Item Group", 
				self.doc.parent_item_group)
		
	def on_update(self):
		DocTypeNestedSet.on_update(self)
		
		self.validate_name_with_item()
		
		self.validate_one_root()
		
	def validate_name_with_item(self):
		if frappe.db.exists("Item", self.doc.name):
			frappe.msgprint("An item exists with same name (%s), please change the \
				item group name or rename the item" % self.doc.name, raise_exception=1)

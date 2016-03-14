# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import _

from frappe.model.document import Document

class ProductBundle(Document):
	def autoname(self):
		self.name = self.new_item_code

	def validate(self):
		self.validate_main_item()
		self.validate_child_items()
		from erpnext.utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self, "uom", "qty")

	def validate_main_item(self):
		"""Validates, main Item is not a stock item"""
		if frappe.db.get_value("Item", self.new_item_code, "is_stock_item"):
			frappe.throw(_("Parent Item {0} must not be a Stock Item").format(self.new_item_code))
			
	def validate_child_items(self):
		for item in self.items:
			if frappe.db.exists("Product Bundle", item.item_code):
				frappe.throw(_("Child Item should not be a Product Bundle. Please remove item `{0}` and save").format(item.item_code))
				
def get_new_item_code(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	return frappe.db.sql("""select name, item_name, description from tabItem
		where is_stock_item=0 and name not in (select name from `tabProduct Bundle`)
		and %s like %s %s limit %s, %s""" % (searchfield, "%s",
		get_match_cond(doctype),"%s", "%s"),
		("%%%s%%" % txt, start, page_len))

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _

class ItemPriceDuplicateItem(frappe.ValidationError): pass

from frappe.model.document import Document

class ItemPrice(Document):
	def validate(self):
		self.validate_item()
		self.validate_price_list()
		self.check_duplicate_item()
		self.update_price_list_details()
		self.update_item_details()

	def validate_item(self):
		if not frappe.db.exists("Item", self.item_code):
			throw(_("Item {0} not found").format(self.item_code))

	def validate_price_list(self):
		enabled = frappe.db.get_value("Price List", self.price_list, "enabled")
		if not enabled:
			throw(_("Price List {0} is disabled").format(self.price_list))

	def check_duplicate_item(self):
		if frappe.db.sql("""select name from `tabItem Price`
			where item_code=%s and price_list=%s and name!=%s""", (self.item_code, self.price_list, self.name)):

			frappe.throw(_("Item {0} appears multiple times in Price List {1}").format(self.item_code, self.price_list),
				ItemPriceDuplicateItem)

	def update_price_list_details(self):
		self.buying, self.selling, self.currency = \
			frappe.db.get_value("Price List", {"name": self.price_list, "enabled": 1},
				["buying", "selling", "currency"])

	def update_item_details(self):
		self.item_name, self.item_description = frappe.db.get_value("Item",
			self.item_code, ["item_name", "description"])

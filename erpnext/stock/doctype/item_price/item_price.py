# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _
from frappe.utils import getdate

class ItemPriceDuplicateItem(frappe.ValidationError): pass

from frappe.model.document import Document

class ItemPrice(Document):
	def validate(self):
		self.validate_item()
		self.validate_price_list()
		self.validate_dates()
		self.update_price_list_details()
		self.update_item_details()

	def validate_dates(self):
		if self.valid_from and self.valid_upto:
			if getdate(self.valid_upto) <= getdate(self.valid_from):
				frappe.throw(_("Valid Upto Date can not be less/equal than Valid From Date"))

	def validate_item(self):
		if not frappe.db.exists("Item", self.item_code):
			throw(_("Item {0} not found").format(self.item_code))

	def validate_price_list(self):
		enabled = frappe.db.get_value("Price List", self.price_list, "enabled")
		if not enabled:
			throw(_("Price List {0} is disabled").format(self.price_list))

	def update_price_list_details(self):
		self.buying, self.selling, self.currency = \
			frappe.db.get_value("Price List", {"name": self.price_list, "enabled": 1},
				["buying", "selling", "currency"])

	def update_item_details(self):
		self.item_name, self.item_description = frappe.db.get_value("Item",
			self.item_code, ["item_name", "description"])

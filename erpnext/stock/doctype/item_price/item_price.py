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
		self.validate_duplicates()
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

	def validate_duplicates(self):
		args = {
			"price_list": self.price_list,
			"customer": self.customer, 
			"currency": self.currency,
			"item_code": self.item_code, 
			"uom": self.uom,
			"valid_from": self.valid_from, 
			"valid_upto": self.valid_upto,
			"min_qty": self.min_qty
		}
		empty_keys = [k for k,v in args.iteritems() if not v]
		for k in empty_keys:
			args[k] = ""

		print str(args)
		count = frappe.db.sql("""SELECT price_list
			FROM `tabItem Price` 
			WHERE (price_list =%(price_list)s OR %(price_list)s = "")
				AND (customer =%(customer)s OR %(customer)s = "")
				AND (currency =%(currency)s  OR %(currency)s = "")
				AND (item_code =%(item_code)s OR %(item_code)s = "")
				AND (uom =%(uom)s OR %(uom)s = "")
				AND (min_qty =%(min_qty)s  OR %(min_qty)s = "")
				AND (valid_from =%(valid_from)s  OR %(valid_from)s = "")
				AND (valid_upto =%(valid_upto)s  OR %(valid_upto)s = "")
				""", args)
				
		if len(count) > 0:
			throw(_("Item Price is a duplicate").format(self.price_list), ItemPriceDuplicateItem)
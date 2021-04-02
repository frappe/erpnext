# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


class ItemPriceDuplicateItem(frappe.ValidationError): pass


from frappe.model.document import Document


class ItemPrice(Document):

	def validate(self):
		self.validate_item()
		self.validate_dates()
		self.update_price_list_details()
		self.update_item_details()
		self.check_duplicates()

	def validate_item(self):
		if not frappe.db.exists("Item", self.item_code):
			frappe.throw(_("Item {0} not found").format(self.item_code))

	def validate_dates(self):
		if self.valid_from and self.valid_upto:
			if self.valid_from > self.valid_upto:
				frappe.throw(_("Valid From Date must be lesser than Valid Upto Date."))

	def update_price_list_details(self):
		if self.price_list:
			price_list_details = frappe.db.get_value("Price List",
				{"name": self.price_list, "enabled": 1},
				["buying", "selling", "currency"])

			if not price_list_details:
				link = frappe.utils.get_link_to_form('Price List', self.price_list)
				frappe.throw("The price list {0} does not exists or disabled".
					format(link))

			self.buying, self.selling, self.currency = price_list_details

	def update_item_details(self):
		if self.item_code:
			self.item_name, self.item_description = frappe.db.get_value("Item",
				self.item_code,["item_name", "description"])

	def check_duplicates(self):
		conditions = "where item_code=%(item_code)s and price_list=%(price_list)s and name != %(name)s"
		condition_data_dict = dict(item_code=self.item_code, price_list=self.price_list, name=self.name)

		for field in ['uom', 'valid_from',
			'valid_upto', 'packing_unit', 'customer', 'supplier']:
			if self.get(field):
				conditions += " and {0} = %({1})s".format(field, field)
				condition_data_dict[field] = self.get(field)

		price_list_rate = frappe.db.sql("""
			SELECT price_list_rate
			FROM `tabItem Price`
			  {conditions} """.format(conditions=conditions), condition_data_dict)

		if price_list_rate :
			frappe.throw(_("Item Price appears multiple times based on Price List, Supplier/Customer, Currency, Item, UOM, Qty and Dates."), ItemPriceDuplicateItem)

	def before_save(self):
		if self.selling:
			self.reference = self.customer
		if self.buying:
			self.reference = self.supplier
		
		if self.selling and not self.buying:
			# if only selling then remove supplier
			self.supplier = None
		if self.buying and not self.selling:
			# if only buying then remove customer
			self.customer = None

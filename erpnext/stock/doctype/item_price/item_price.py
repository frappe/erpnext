# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Cast_
from frappe.utils import getdate


class ItemPriceDuplicateItem(frappe.ValidationError):
	pass


class ItemPrice(Document):
	def validate(self):
		self.validate_item()
		self.validate_dates()
		self.update_price_list_details()
		self.update_item_details()
		self.check_duplicates()

	def validate_item(self):
		if not frappe.db.exists("Item", self.item_code):
			frappe.throw(_("Item {0} not found.").format(self.item_code))

	def validate_dates(self):
		if self.valid_from and self.valid_upto:
			if getdate(self.valid_from) > getdate(self.valid_upto):
				frappe.throw(_("Valid From Date must be lesser than Valid Upto Date."))

	def update_price_list_details(self):
		if self.price_list:
			price_list_details = frappe.db.get_value(
				"Price List", {"name": self.price_list, "enabled": 1}, ["buying", "selling", "currency"]
			)

			if not price_list_details:
				link = frappe.utils.get_link_to_form("Price List", self.price_list)
				frappe.throw("The price list {0} does not exist or is disabled".format(link))

			self.buying, self.selling, self.currency = price_list_details

	def update_item_details(self):
		if self.item_code:
			self.item_name, self.item_description = frappe.db.get_value(
				"Item", self.item_code, ["item_name", "description"]
			)

	def check_duplicates(self):

		item_price = frappe.qb.DocType("Item Price")

		query = (
			frappe.qb.from_(item_price)
			.select(item_price.price_list_rate)
			.where(
				(item_price.item_code == self.item_code)
				& (item_price.price_list == self.price_list)
				& (item_price.name != self.name)
			)
		)
		data_fields = (
			"uom",
			"valid_from",
			"valid_upto",
			"customer",
			"supplier",
			"batch_no",
		)

		number_fields = ["packing_unit"]

		for field in data_fields:
			if self.get(field):
				query = query.where(item_price[field] == self.get(field))
			else:
				query = query.where(
					Criterion.any(
						[
							item_price[field].isnull(),
							Cast_(item_price[field], "varchar") == "",
						]
					)
				)

		for field in number_fields:
			if self.get(field):
				query = query.where(item_price[field] == self.get(field))
			else:
				query = query.where(
					Criterion.any(
						[
							item_price[field].isnull(),
							item_price[field] == 0,
						]
					)
				)

		price_list_rate = query.run(as_dict=True)

		if price_list_rate:
			frappe.throw(
				_(
					"Item Price appears multiple times based on Price List, Supplier/Customer, Currency, Item, Batch, UOM, Qty, and Dates."
				),
				ItemPriceDuplicateItem,
			)

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

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Cast_


class ItemPriceDuplicateItem(frappe.ValidationError):
	pass


class ItemPrice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		batch_no: DF.Link | None
		brand: DF.Link | None
		buying: DF.Check
		currency: DF.Link | None
		customer: DF.Link | None
		item_code: DF.Link
		item_description: DF.Text | None
		item_name: DF.Data | None
		lead_time_days: DF.Int
		note: DF.Text | None
		packing_unit: DF.Int
		price_list: DF.Link
		price_list_rate: DF.Currency
		reference: DF.Data | None
		selling: DF.Check
		supplier: DF.Link | None
		uom: DF.Link
		valid_from: DF.Date | None
		valid_upto: DF.Date | None
	# end: auto-generated types

	def validate(self):
		self.validate_item()
		self.validate_from_to_dates("valid_from", "valid_upto")
		self.update_price_list_details()
		self.update_item_details()
		self.check_duplicates()
		self.validate_item_template()

	def validate_item(self):
		if not frappe.db.exists("Item", self.item_code):
			frappe.throw(_("Item {0} not found.").format(self.item_code))

	def update_price_list_details(self):
		if self.price_list:
			price_list_details = frappe.db.get_value(
				"Price List", {"name": self.price_list, "enabled": 1}, ["buying", "selling", "currency"]
			)

			if not price_list_details:
				link = frappe.utils.get_link_to_form("Price List", self.price_list)
				frappe.throw(f"The price list {link} does not exist or is disabled")

			self.buying, self.selling, self.currency = price_list_details

	def update_item_details(self):
		if self.item_code:
			self.item_name, self.item_description = frappe.db.get_value(
				"Item", self.item_code, ["item_name", "description"]
			)

	def validate_item_template(self):
		if frappe.get_cached_value("Item", self.item_code, "has_variants"):
			msg = f"Item Price cannot be created for the template item {bold(self.item_code)}"

			frappe.throw(_(msg))

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

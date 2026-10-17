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
		item_description: DF.TextEditor | None
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
		self.clear_party_not_applicable()
		self.update_item_details()
		self.validate_batch()
		self.check_duplicates()
		self.validate_item_template()

	def validate_item(self):
		if not frappe.db.exists("Item", self.item_code):
			frappe.throw(_("Item {0} not found.").format(self.item_code))

		if self.uom and not frappe.db.exists(
			"UOM Conversion Detail", {"parenttype": "Item", "parent": self.item_code, "uom": self.uom}
		):
			frappe.throw(_("UOM {0} not found in Item {1}").format(self.uom, self.item_code))

	def update_price_list_details(self):
		if self.price_list:
			price_list_details = frappe.db.get_value(
				"Price List", {"name": self.price_list, "enabled": 1}, ["buying", "selling", "currency"]
			)

			if not price_list_details:
				link = frappe.utils.get_link_to_form("Price List", self.price_list)
				frappe.throw(_("The price list {0} does not exist or is disabled").format(link))

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
		if self.get_duplicate_price_query().run():
			frappe.throw(
				_(
					"Item Price appears multiple times based on Price List, Supplier/Customer, Currency, Item, Batch, UOM, Qty, and Dates."
				),
				ItemPriceDuplicateItem,
			)

	def get_duplicate_price_query(self):
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

		for field in ("uom", "valid_from", "customer", "supplier", "batch_no"):
			query = query.where(
				self.get_match_condition(item_price[field], Cast_(item_price[field], "varchar") == "")
			)

		return query.where(self.get_match_condition(item_price.packing_unit, item_price.packing_unit == 0))

	def get_match_condition(self, column, empty_condition):
		if value := self.get(column.name):
			return column == value

		return Criterion.any([column.isnull(), empty_condition])

	def clear_party_not_applicable(self):
		if self.selling and not self.buying:
			self.supplier = None
		if self.buying and not self.selling:
			self.customer = None

	def validate_batch(self):
		if self.batch_no and frappe.db.get_value("Batch", self.batch_no, "item") != self.item_code:
			frappe.throw(
				_("Batch {0} does not belong to Item {1}").format(bold(self.batch_no), bold(self.item_code))
			)

	def before_save(self):
		if self.selling:
			self.reference = self.customer
		if self.buying:
			self.reference = self.supplier

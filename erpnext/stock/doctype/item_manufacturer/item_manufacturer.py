# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class ItemManufacturer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		is_default: DF.Check
		item_code: DF.Link
		item_name: DF.Data | None
		manufacturer: DF.Link
		manufacturer_part_no: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_duplicate_entry()
		self.manage_default_item_manufacturer()

	def on_trash(self):
		self.manage_default_item_manufacturer(delete=True)

	def validate_duplicate_entry(self):
		if self.is_new():
			filters = {
				"item_code": self.item_code,
				"manufacturer": self.manufacturer,
				"manufacturer_part_no": self.manufacturer_part_no,
			}

			if frappe.db.exists("Item Manufacturer", filters):
				frappe.throw(
					_("Duplicate entry against the item code {0} and manufacturer {1}").format(
						self.item_code, self.manufacturer
					)
				)

	def manage_default_item_manufacturer(self, delete=False):
		from frappe.model.utils import set_default

		item = frappe.get_doc("Item", self.item_code)
		default_manufacturer = item.default_item_manufacturer
		default_part_no = item.default_manufacturer_part_no

		if not self.is_default:
			# if unchecked and default in Item master, clear it.
			if default_manufacturer == self.manufacturer and default_part_no == self.manufacturer_part_no:
				frappe.db.set_value(
					"Item",
					item.name,
					{"default_item_manufacturer": None, "default_manufacturer_part_no": None},
				)

		elif self.is_default:
			set_default(self, "item_code")
			manufacturer, manufacturer_part_no = default_manufacturer, default_part_no

			if delete:
				manufacturer, manufacturer_part_no = None, None

			elif (default_manufacturer != self.manufacturer) or (
				default_manufacturer == self.manufacturer and default_part_no != self.manufacturer_part_no
			):
				manufacturer = self.manufacturer
				manufacturer_part_no = self.manufacturer_part_no

			frappe.db.set_value(
				"Item",
				item.name,
				{
					"default_item_manufacturer": manufacturer,
					"default_manufacturer_part_no": manufacturer_part_no,
				},
			)


@frappe.whitelist()
def get_item_manufacturer_part_no(item_code, manufacturer):
	return frappe.db.get_value(
		"Item Manufacturer",
		{"item_code": item_code, "manufacturer": manufacturer},
		"manufacturer_part_no",
	)

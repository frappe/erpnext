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
		filters = {
			"item_code": self.item_code,
			"manufacturer": self.manufacturer,
			"manufacturer_part_no": self.manufacturer_part_no,
			"name": ("!=", self.name),
		}

		if frappe.db.exists("Item Manufacturer", filters):
			frappe.throw(
				_("Duplicate entry against the item code {0} and manufacturer {1}").format(
					self.item_code, self.manufacturer
				)
			)

	def manage_default_item_manufacturer(self, delete=False):
		from frappe.model.utils import set_default

		if self.is_default and not delete:
			set_default(self, "item_code")
			self.set_item_default(self.manufacturer, self.manufacturer_part_no)
		elif self.is_item_default():
			self.set_item_default(None, None)

	def is_item_default(self):
		if not self.is_default and not (self.get_doc_before_save() or {}).get("is_default"):
			return False

		item_default = frappe.db.get_value(
			"Item", self.item_code, ["default_item_manufacturer", "default_manufacturer_part_no"]
		)
		return tuple(item_default) == (self.manufacturer, self.manufacturer_part_no)

	def set_item_default(self, manufacturer, manufacturer_part_no):
		frappe.db.set_value(
			"Item",
			self.item_code,
			{"default_item_manufacturer": manufacturer, "default_manufacturer_part_no": manufacturer_part_no},
		)


@frappe.whitelist()
def get_item_manufacturer_part_no(item_code: str, manufacturer: str):
	return frappe.db.get_value(
		"Item Manufacturer",
		{"item_code": item_code, "manufacturer": manufacturer},
		"manufacturer_part_no",
	)

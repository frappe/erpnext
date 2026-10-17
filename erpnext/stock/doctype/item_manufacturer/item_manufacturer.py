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
		if self.is_default:
			self.clear_item_default(self)

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

	def manage_default_item_manufacturer(self):
		from frappe.model.utils import set_default

		previous = self.get_doc_before_save()
		if previous and previous.is_default and self.has_default_changed(previous):
			self.clear_item_default(previous)

		if self.is_default:
			set_default(self, "item_code")
			self.set_item_default(self.item_code, self.manufacturer, self.manufacturer_part_no)

	def has_default_changed(self, previous):
		fieldnames = ("is_default", "item_code", "manufacturer", "manufacturer_part_no")
		return any(previous.get(fieldname) != self.get(fieldname) for fieldname in fieldnames)

	def clear_item_default(self, row):
		item_default = frappe.db.get_value(
			"Item", row.item_code, ["default_item_manufacturer", "default_manufacturer_part_no"]
		)
		if tuple(item_default or ()) == (row.manufacturer, row.manufacturer_part_no):
			self.set_item_default(row.item_code, None, None)

	def set_item_default(self, item_code, manufacturer, manufacturer_part_no):
		frappe.has_permission("Item", "write", doc=item_code, throw=True)
		frappe.db.set_value(
			"Item",
			item_code,
			{"default_item_manufacturer": manufacturer, "default_manufacturer_part_no": manufacturer_part_no},
		)


@frappe.whitelist()
def get_item_manufacturer_part_no(item_code: str, manufacturer: str):
	return frappe.db.get_value(
		"Item Manufacturer",
		{"item_code": item_code, "manufacturer": manufacturer},
		"manufacturer_part_no",
	)

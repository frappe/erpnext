# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class ItemAlternative(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		alternative_item_code: DF.Link | None
		alternative_item_name: DF.ReadOnly | None
		item_code: DF.Link | None
		item_name: DF.ReadOnly | None
		two_way: DF.Check
	# end: auto-generated types

	def validate(self):
		self.has_alternative_item()
		self.validate_alternative_item()
		self.validate_duplicate()

	def has_alternative_item(self):
		if self.item_code and not frappe.db.get_value("Item", self.item_code, "allow_alternative_item"):
			frappe.throw(_("Cannot set alternative item for the item {0}").format(self.item_code))

	def validate_alternative_item(self):
		if self.item_code == self.alternative_item_code:
			frappe.throw(_("Alternative item must not be same as item code"))

		item_meta = frappe.get_meta("Item")
		fields = [
			"is_stock_item",
			"include_item_in_manufacturing",
			"has_serial_no",
			"has_batch_no",
			"allow_alternative_item",
		]
		item_data = frappe.db.get_value("Item", self.item_code, fields, as_dict=1)
		alternative_item_data = frappe.db.get_value("Item", self.alternative_item_code, fields, as_dict=1)

		for field in fields:
			if item_data.get(field) != alternative_item_data.get(field):
				raise_exception, alert = [1, False] if field == "is_stock_item" else [0, True]

				frappe.msgprint(
					_("The value of {0} differs between Items {1} and {2}").format(
						frappe.bold(item_meta.get_label(field)),
						frappe.bold(self.alternative_item_code),
						frappe.bold(self.item_code),
					),
					alert=alert,
					raise_exception=raise_exception,
					indicator="Orange",
				)

		alternate_item_check_msg = _("Allow Alternative Item must be checked on Item {0}")

		if not item_data.allow_alternative_item:
			frappe.throw(alternate_item_check_msg.format(self.item_code))
		if self.two_way and not alternative_item_data.allow_alternative_item:
			frappe.throw(alternate_item_check_msg.format(self.alternative_item_code))

	def validate_duplicate(self):
		if frappe.db.get_value(
			"Item Alternative",
			{
				"item_code": self.item_code,
				"alternative_item_code": self.alternative_item_code,
				"name": ("!=", self.name),
			},
		):
			frappe.throw(_("Record already exists for the item {0}").format(self.item_code))


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_alternative_items(doctype: Any, txt: str, searchfield: Any, start: int, page_len: int, filters: dict):
	item_code = filters.get("item_code")
	search = f"%{txt}%"
	# each leg has distinct values (validate_duplicate), so start+page_len rows per leg suffice
	limit = cint(start) + cint(page_len)

	alternatives = frappe.get_all(
		"Item Alternative",
		filters={"item_code": item_code, "alternative_item_code": ["like", search]},
		pluck="alternative_item_code",
		limit=limit,
	)
	alternatives += frappe.get_all(
		"Item Alternative",
		filters={"alternative_item_code": item_code, "item_code": ["like", search], "two_way": 1},
		pluck="item_code",
		limit=limit,
	)

	# union (dedupe, preserve order) + paginate
	unique_items = list(dict.fromkeys(alternatives))
	return [[item] for item in unique_items[start : start + page_len]]

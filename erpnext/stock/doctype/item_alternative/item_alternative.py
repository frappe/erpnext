# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class ItemAlternative(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		alternative_item_code: DF.Link
		alternative_item_name: DF.ReadOnly | None
		item_code: DF.Link
		item_name: DF.ReadOnly | None
		two_way: DF.Check
	# end: auto-generated types

	def validate(self):
		if not (self.item_code and self.alternative_item_code):
			return

		self.has_alternative_item()
		self.validate_alternative_item()
		self.validate_duplicate()

	def has_alternative_item(self):
		if self.item_code and not frappe.db.get_value("Item", self.item_code, "allow_alternative_item"):
			frappe.throw(_("Not allow to set alternative item for the item {0}").format(self.item_code))

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

		alternate_item_check_msg = _("Allow Alternative Item must be checked on Item {}")

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
			frappe.throw(_("Already record exists for the item {0}").format(self.item_code))


def get_alternative_item_pairs(item_codes) -> set:
	if not item_codes:
		return set()

	item_alternative = frappe.qb.DocType("Item Alternative")
	rows = (
		frappe.qb.from_(item_alternative)
		.select(item_alternative.item_code, item_alternative.alternative_item_code, item_alternative.two_way)
		.where(
			(item_alternative.item_code.isin(item_codes))
			| ((item_alternative.alternative_item_code.isin(item_codes)) & (item_alternative.two_way == 1))
		)
	).run(as_dict=True)

	pairs = set()
	for row in rows:
		pairs.add((row.item_code, row.alternative_item_code))
		if row.two_way:
			pairs.add((row.alternative_item_code, row.item_code))

	return pairs


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_alternative_items(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		f""" (select alternative_item_code from `tabItem Alternative`
			where item_code = %(item_code)s and alternative_item_code like %(txt)s)
		union
			(select item_code from `tabItem Alternative`
			where alternative_item_code = %(item_code)s and item_code like %(txt)s
			and two_way = 1) limit {page_len} offset {start}
		""",
		{"item_code": filters.get("item_code"), "txt": "%" + txt + "%"},
	)

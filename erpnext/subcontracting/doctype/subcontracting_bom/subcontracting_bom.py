# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.controllers.queries import bom
from erpnext.stock.get_item_details import get_default_bom


class SubcontractingBOM(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		conversion_factor: DF.Float
		finished_good: DF.Link
		finished_good_bom: DF.Link
		finished_good_qty: DF.Float
		finished_good_uom: DF.Link | None
		is_active: DF.Check
		service_item: DF.Link
		service_item_qty: DF.Float
		service_item_uom: DF.Link
	# end: auto-generated types

	def validate(self):
		self.validate_finished_good()
		self.validate_finished_good_bom()
		self.validate_service_item()
		self.validate_is_active()

	def before_save(self):
		self.set_conversion_factor()

	def validate_finished_good(self):
		disabled, is_stock_item, is_sub_contracted_item = frappe.db.get_value(
			"Item",
			self.finished_good,
			["disabled", "is_stock_item", "is_sub_contracted_item"],
		)

		if disabled:
			frappe.throw(_("Finished Good {0} is disabled.").format(frappe.bold(self.finished_good)))
		if not is_stock_item:
			frappe.throw(_("Finished Good {0} must be a stock item.").format(frappe.bold(self.finished_good)))
		if not get_default_bom(self.finished_good):
			frappe.throw(
				_("Finished Good {0} does not have a default BOM.").format(frappe.bold(self.finished_good))
			)
		if not is_sub_contracted_item:
			frappe.throw(
				_("Finished Good {0} must be a sub-contracted item.").format(frappe.bold(self.finished_good))
			)

	def validate_finished_good_bom(self):
		bom_item = frappe.db.get_value("BOM", self.finished_good_bom, "item")
		if bom_item not in get_applicable_bom_items(self.finished_good):
			frappe.throw(
				_("BOM {0} does not belong to Item {1}").format(
					frappe.bold(self.finished_good_bom), frappe.bold(self.finished_good)
				)
			)

	def validate_service_item(self):
		disabled, is_stock_item = frappe.db.get_value(
			"Item", self.service_item, ["disabled", "is_stock_item"]
		)

		if disabled:
			frappe.throw(_("Service Item {0} is disabled.").format(frappe.bold(self.service_item)))
		if is_stock_item:
			frappe.throw(
				_("Service Item {0} must be a non-stock item.").format(frappe.bold(self.service_item))
			)

	def validate_is_active(self):
		if self.is_active:
			if sb := frappe.db.exists(
				"Subcontracting BOM",
				{"finished_good": self.finished_good, "is_active": 1, "name": ["!=", self.name]},
			):
				frappe.throw(
					_("There is already an active Subcontracting BOM {0} for the Finished Good {1}.").format(
						frappe.bold(sb), frappe.bold(self.finished_good)
					)
				)

	def set_conversion_factor(self):
		self.conversion_factor = flt(self.service_item_qty) / flt(self.finished_good_qty)


def get_finished_good_bom(item: Document) -> str | None:
	"""BOM of the active Subcontracting BOM, else the default BOM of the item or its template."""
	return (
		frappe.db.get_value(
			"Subcontracting BOM", {"finished_good": item.name, "is_active": 1}, "finished_good_bom"
		)
		or item.default_bom
		or get_default_bom(item.variant_of)
	)


def get_applicable_bom_items(item_code: str) -> list[str]:
	"""Items whose BOMs can be used for `item_code`: the item and its template."""
	template = frappe.get_cached_value("Item", item_code, "variant_of")
	return [item_code, template] if template else [item_code]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def finished_good_bom_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | str | None = None
):
	"""BOMs of the finished good and of its template."""
	filters = frappe.parse_json(filters) or {}
	if finished_good := filters.pop("finished_good", None):
		filters["item"] = ["in", get_applicable_bom_items(finished_good)]
	return bom(doctype, txt, searchfield, start, page_len, filters)


@frappe.whitelist()
def get_subcontracting_boms_for_finished_goods(fg_items: str | list):
	if fg_items:
		filters = {"is_active": 1}

		if isinstance(fg_items, list):
			filters["finished_good"] = ["in", fg_items]
		else:
			filters["finished_good"] = fg_items

		if subcontracting_boms := frappe.get_all("Subcontracting BOM", filters=filters, fields=["*"]):
			if isinstance(fg_items, list):
				return {d.finished_good: d for d in subcontracting_boms}
			else:
				return subcontracting_boms[0]

	return frappe._dict({})


@frappe.whitelist()
def get_subcontracting_boms_for_service_item(service_item: str) -> dict:
	if service_item:
		filters = {"is_active": 1, "service_item": service_item}
		Subcontracting_boms = frappe.db.get_all("Subcontracting BOM", filters=filters, fields=["*"])

		if Subcontracting_boms:
			return {d.finished_good: d for d in Subcontracting_boms}

	return {}

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Subcontracting (inward) integration for Sales Order."""

import frappe
from frappe import _


class SubcontractingService:
	def __init__(self, doc):
		self.doc = doc

	def validate_fg_item_for_subcontracting(self) -> None:
		doc = self.doc
		if doc.is_subcontracted:
			for item in doc.items:
				if not item.fg_item:
					frappe.throw(
						_("Row #{0}: Finished Good Item is not specified for service item {1}").format(
							item.idx, item.item_code
						)
					)
				else:
					if not frappe.get_value("Item", item.fg_item, "is_sub_contracted_item"):
						frappe.throw(
							_("Row #{0}: Finished Good Item {1} must be a sub-contracted item").format(
								item.idx, item.fg_item
							)
						)
					if not frappe.db.get_value(
						"Subcontracting BOM",
						{"finished_good": item.fg_item, "is_active": 1},
						"finished_good_bom",
					) and not frappe.get_value("Item", item.fg_item, "default_bom"):
						frappe.throw(
							_("Row #{0}: BOM not found for FG Item {1}").format(item.idx, item.fg_item)
						)
				if not item.fg_item_qty:
					frappe.throw(_("Row #{0}: Finished Good Item Qty can not be zero").format(item.idx))
		else:
			for item in doc.items:
				item.set("fg_item", None)
				item.set("fg_item_qty", 0)

	def can_update_items(self) -> bool:
		result = True

		if self.doc.is_subcontracted:
			if frappe.db.exists(
				"Subcontracting Inward Order", {"sales_order": self.doc.name, "docstatus": 1}
			):
				result = False

		return result

	def update_subcontracting_order_status(self) -> None:
		from erpnext.subcontracting.doctype.subcontracting_inward_order.subcontracting_inward_order import (
			update_subcontracting_inward_order_status as update_scio_status,
		)

		doc = self.doc
		if doc.is_subcontracted:
			scio = frappe.get_cached_value(
				"Subcontracting Inward Order", {"sales_order": doc.name, "docstatus": 1}, "name"
			)

			if scio:
				update_scio_status(scio, "Closed" if doc.status == "Closed" else None)

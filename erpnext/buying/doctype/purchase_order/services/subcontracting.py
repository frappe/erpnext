# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Subcontracting integration for Purchase Order."""

import frappe
from frappe import _
from frappe.utils import flt


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
					elif not item.bom and not frappe.get_value("Item", item.fg_item, "default_bom"):
						frappe.throw(
							_("Row #{0}: Default BOM not found for FG Item {1}").format(
								item.idx, item.fg_item
							)
						)
				if not item.fg_item_qty:
					frappe.throw(_("Row #{0}: Finished Good Item Qty can not be zero").format(item.idx))
		else:
			for item in doc.items:
				item.set("fg_item", None)
				item.set("fg_item_qty", 0)

	def set_service_items_for_finished_goods(self) -> None:
		from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import (
			get_subcontracting_boms_for_finished_goods,
		)

		doc = self.doc
		if not doc.is_subcontracted:
			return

		finished_goods_without_service_item = {
			d.fg_item for d in doc.items if (not d.item_code and d.fg_item)
		}

		if subcontracting_boms := get_subcontracting_boms_for_finished_goods(
			finished_goods_without_service_item
		):
			for item in doc.items:
				if not item.item_code and item.fg_item in subcontracting_boms:
					subcontracting_bom = subcontracting_boms[item.fg_item]

					item.item_code = subcontracting_bom.service_item
					item.qty = flt(item.fg_item_qty) * flt(subcontracting_bom.conversion_factor)
					item.uom = subcontracting_bom.service_item_uom

	def can_update_items(self) -> bool:
		result = True

		if self.doc.is_subcontracted:
			if frappe.db.exists(
				"Subcontracting Order", {"purchase_order": self.doc.name, "docstatus": ["!=", 2]}
			):
				result = False

		return result

	def auto_create_subcontracting_order(self) -> None:
		from erpnext.buying.doctype.purchase_order.mapper import make_subcontracting_order

		if self.doc.is_subcontracted:
			if frappe.db.get_single_value("Buying Settings", "auto_create_subcontracting_order"):
				make_subcontracting_order(self.doc.name, save=True, notify=True)

	def update_subcontracting_order_status(self) -> None:
		from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
			update_subcontracting_order_status as update_sco_status,
		)

		doc = self.doc
		if doc.is_subcontracted:
			sco = frappe.db.get_value("Subcontracting Order", {"purchase_order": doc.name, "docstatus": 1})

			if sco:
				update_sco_status(sco, "Closed" if doc.status == "Closed" else None)

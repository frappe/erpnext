# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Packing slip and product bundle handling for Delivery Note."""

import frappe
from frappe import _
from frappe.utils import flt


class PackingService:
	def __init__(self, doc):
		self.doc = doc

	def validate_packed_qty(self) -> None:
		"""Validate that if packed qty exists, it should be equal to qty"""
		doc = self.doc

		if frappe.db.exists("Packing Slip", {"docstatus": 1, "delivery_note": doc.name}):
			product_bundle_list = self.get_product_bundle_list()
			for item in doc.items + doc.packed_items:
				if (
					item.item_code not in product_bundle_list
					and flt(item.packed_qty)
					and flt(item.packed_qty) != flt(item.qty)
				):
					frappe.throw(
						_("Row {0}: Packed Qty must be equal to {1} Qty.").format(
							item.idx, frappe.bold(item.doctype)
						)
					)

	def has_unpacked_items(self) -> bool:
		doc = self.doc
		product_bundle_list = self.get_product_bundle_list()

		for item in doc.items + doc.packed_items:
			if item.item_code not in product_bundle_list and flt(item.packed_qty) < flt(item.qty):
				return True

		return False

	def get_product_bundle_list(self) -> list[str]:
		items_list = [item.item_code for item in self.doc.items]
		return frappe.db.get_all(
			"Product Bundle",
			filters={"new_item_code": ["in", items_list], "is_active": 1, "docstatus": 1},
			pluck="name",
		)

	def cancel_packing_slips(self) -> None:
		"""Cancel submitted packing slips related to this delivery note"""
		res = frappe.db.sql(
			"""SELECT name FROM `tabPacking Slip` WHERE delivery_note = %s
			AND docstatus = 1""",
			self.doc.name,
		)

		if res:
			for r in res:
				ps = frappe.get_doc("Packing Slip", r[0])
				ps.cancel()
			frappe.msgprint(_("Packing Slip(s) cancelled"))

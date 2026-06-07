# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Stock reservation logic for Sales Order."""

from typing import Literal

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	get_sre_reserved_qty_details_for_voucher,
)
from erpnext.stock.stock_balance import get_reserved_qty, update_bin_qty


class StockReservationService:
	def __init__(self, doc):
		self.doc = doc

	def validate_reserved_stock(self) -> None:
		"""Clean reserved stock flag for non-stock Item"""

		enable_stock_reservation = frappe.get_single_value("Stock Settings", "enable_stock_reservation")

		for item in self.doc.items:
			if item.reserve_stock and (not enable_stock_reservation or not cint(item.is_stock_item)):
				item.reserve_stock = 0

	def enable_auto_reserve_stock(self) -> None:
		if self.doc.is_new() and frappe.get_single_value("Stock Settings", "auto_reserve_stock"):
			self.doc.reserve_stock = 1

	def update_reserved_qty(self, so_item_rows: list | None = None) -> None:
		"""update requested qty (before ordered_qty is updated)"""
		item_wh_list = []

		def _valid_for_reserve(item_code, warehouse):
			if (
				item_code
				and warehouse
				and [item_code, warehouse] not in item_wh_list
				and frappe.get_cached_value("Item", item_code, "is_stock_item")
			):
				item_wh_list.append([item_code, warehouse])

		for d in self.doc.get("items"):
			if (not so_item_rows or d.name in so_item_rows) and not d.delivered_by_supplier:
				if self.doc.has_product_bundle(d.item_code):
					for p in self.doc.get("packed_items"):
						if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
							_valid_for_reserve(p.item_code, p.warehouse)
				else:
					_valid_for_reserve(d.item_code, d.warehouse)

		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {"reserved_qty": get_reserved_qty(item_code, warehouse)})

	def has_unreserved_stock(self, table_name: str = "items") -> dict:
		"""Returns unreserved qty per item if there is any unreserved item in the Sales Order."""

		reserved_qty_details = get_sre_reserved_qty_details_for_voucher("Sales Order", self.doc.name)

		data = {}
		for item in self.doc.get(table_name):
			if not item.get("reserve_stock"):
				continue

			unreserved_qty = get_unreserved_qty(item, reserved_qty_details)
			if unreserved_qty > 0:
				data[item.name] = unreserved_qty

		return data

	def create_stock_reservation_entries(
		self,
		items_details: list[dict] | None = None,
		from_voucher_type: Literal["Pick List", "Purchase Receipt"] | None = None,
		notify: bool = True,
	) -> None:
		"""Creates Stock Reservation Entries for Sales Order Items."""

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			create_stock_reservation_entries_for_so_items as create_stock_reservation_entries,
		)

		packed_items = []
		if items_details:
			for item in items_details:
				if not frappe.db.exists("Sales Order Item", item.get("sales_order_item")):
					item["qty"] = item.pop("qty_to_reserve")
					packed_items.append(item)

			for item in packed_items:
				items_details.remove(item)

		sre_count = 0
		if items_details != []:
			sre_count = create_stock_reservation_entries(
				sales_order=self.doc,
				items_details=items_details,
				from_voucher_type=from_voucher_type,
				notify=notify,
			)

		items = []
		if packed_items:
			items = packed_items
		elif not items_details:
			items = [item for item in self.doc.packed_items if item.reserve_stock]

		if items:
			from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import StockReservation

			stock_reservation = StockReservation(doc=self.doc, items=items)
			stock_reservation.table_name = "packed_items"
			stock_reservation.qty_field = "qty"
			is_sre_created = stock_reservation.make_stock_reservation_entries()

			if notify and is_sre_created and not sre_count:
				frappe.msgprint(_("Stock Reservation Entries Created"), alert=True, indicator="green")

	def cancel_stock_reservation_entries(self, sre_list: list | None = None, notify: bool = True) -> None:
		"""Cancel Stock Reservation Entries for Sales Order Items."""

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)

		cancel_stock_reservation_entries(
			voucher_type=self.doc.doctype, voucher_no=self.doc.name, sre_list=sre_list, notify=notify
		)


def get_unreserved_qty(item: object, reserved_qty_details: dict) -> float:
	"""Returns the unreserved quantity for the Sales Order Item."""

	existing_reserved_qty = reserved_qty_details.get(item.name, 0)
	if item.get("delivered_qty") is not None:
		return (
			item.stock_qty
			- flt(item.delivered_qty) * item.get("conversion_factor", 1)
			- existing_reserved_qty
		)
	else:
		stock_qty, delivered_qty, conversion_factor = frappe.get_value(
			"Sales Order Item",
			item.parent_detail_docname,
			["stock_qty", "delivered_qty", "conversion_factor"],
		)
		bundle_conversion_factor = (
			item.qty / stock_qty
		)  # ratio of packed item qty to main item qty in product bundle
		delivered_qty = delivered_qty * conversion_factor * bundle_conversion_factor
		return item.qty - delivered_qty - existing_reserved_qty

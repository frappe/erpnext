# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Stock reservation on Purchase Receipt submission (Sales Order / Production Plan)."""

import frappe
from frappe import _
from frappe.utils import get_datetime

from erpnext.manufacturing.doctype.production_plan.services.reservation import reserve_received_stock


class PurchaseReceiptStockReservation:
	def __init__(self, doc):
		self.doc = doc

	def reserve_stock(self) -> None:
		self.reserve_stock_for_sales_order()
		self.reserve_stock_for_production_plan()

	def reserve_stock_for_sales_order(self) -> None:
		doc = self.doc
		if (
			doc.is_return
			or not frappe.get_single_value("Stock Settings", "enable_stock_reservation")
			or not frappe.get_single_value("Stock Settings", "auto_reserve_stock_for_sales_order_on_purchase")
		):
			return

		doc.reload()  # reload to get the Serial and Batch Bundle Details

		so_items_details_map = {}
		for item in doc.items:
			if item.sales_order and item.sales_order_item:
				item_details = {
					"sales_order_item": item.sales_order_item,
					"item_code": item.item_code,
					"warehouse": item.warehouse,
					"qty_to_reserve": item.stock_qty,
					"from_voucher_no": item.parent,
					"from_voucher_detail_no": item.name,
					"serial_and_batch_bundle": item.serial_and_batch_bundle,
				}
				so_items_details_map.setdefault(item.sales_order, []).append(item_details)

		if so_items_details_map:
			if get_datetime(f"{doc.posting_date} {doc.posting_time}") > get_datetime():
				return frappe.msgprint(
					_("Cannot create Stock Reservation Entries for future dated Purchase Receipts.")
				)

			from erpnext.selling.doctype.sales_order.services.reservation import SalesOrderStockReservation

			for so, items_details in so_items_details_map.items():
				SalesOrderStockReservation(
					frappe.get_lazy_doc("Sales Order", so)
				).create_stock_reservation_entries(
					items_details=items_details,
					from_voucher_type="Purchase Receipt",
					notify=True,
				)

	def reserve_stock_for_production_plan(self) -> None:
		reserve_received_stock(self.doc)

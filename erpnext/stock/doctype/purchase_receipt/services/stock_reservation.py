# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Stock reservation on Purchase Receipt submission (Sales Order / Production Plan)."""

import frappe
from frappe import _
from frappe.utils import get_datetime

from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import StockReservation


class StockReservationService:
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

			for so, items_details in so_items_details_map.items():
				so_doc = frappe.get_lazy_doc("Sales Order", so)
				so_doc.create_stock_reservation_entries(
					items_details=items_details,
					from_voucher_type="Purchase Receipt",
					notify=True,
				)

	def reserve_stock_for_production_plan(self) -> None:
		doc = self.doc
		if doc.is_return or not frappe.get_single_value("Stock Settings", "enable_stock_reservation"):
			return

		production_plan_references = self.get_production_plan_references()
		production_plan_items = []
		doc.reload()

		docnames = []
		for row in doc.items:
			if row.material_request_item and row.material_request_item in production_plan_references:
				_ref = production_plan_references[row.material_request_item]
				docnames.append(_ref.production_plan)
				row.update(
					{
						"voucher_type": "Production Plan",
						"voucher_no": _ref.production_plan,
						"voucher_detail_no": _ref.material_request_plan_item,
						"from_voucher_no": doc.name,
						"from_voucher_detail_no": row.name,
						"from_voucher_type": doc.doctype,
						"serial_and_batch_bundles": [row.serial_and_batch_bundle],
					}
				)

				production_plan_items.append(row)

		if not production_plan_items:
			return

		sre = StockReservation(doc=doc, items=production_plan_items)
		sre.make_stock_reservation_entries()
		if docnames:
			sre.transfer_reservation_entries_to(
				docnames, from_doctype="Production Plan", to_doctype="Work Order"
			)

	def get_production_plan_references(self) -> frappe._dict:
		production_plan_references = frappe._dict()
		material_request_items = []

		for row in self.doc.items:
			if row.material_request_item:
				material_request_items.append(row.material_request_item)

		if not material_request_items:
			return frappe._dict()

		items = frappe.get_all(
			"Material Request Item",
			fields=["material_request_plan_item", "production_plan", "name"],
			filters={"name": ["in", material_request_items], "docstatus": 1},
		)

		for item in items:
			if not item.production_plan:
				continue

			production_plan_references.setdefault(item.name, item)

		return production_plan_references

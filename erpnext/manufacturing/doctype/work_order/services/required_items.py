# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Required-items (raw material) management for Work Order.

Extracted from work_order.py. ``RequiredItemsService`` wraps a Work Order
document (composition); work_order.py keeps thin delegating stubs so external
callers and the whitelisted entry point keep working unchanged.
"""

import frappe
from frappe.utils import flt
from pypika import functions as fn

from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
from erpnext.manufacturing.doctype.work_order.mapper import check_if_scrap_warehouse_mandatory
from erpnext.manufacturing.doctype.work_order.services.stock_reservation import (
	StockReservationService,
	get_consumed_qty,
	get_row_wise_serial_batch,
)
from erpnext.stock.utils import get_bin, get_latest_stock_qty


class RequiredItemsService:
	def __init__(self, doc):
		self.doc = doc

	def update_required_items(self):
		"""
		update bin reserved_qty_for_production
		called from Stock Entry for production, after submit, cancel
		"""
		if self.doc.docstatus == 1:
			self.update_returned_qty()

		# calculate consumed qty based on submitted stock entries
		self.update_consumed_qty_for_required_items()

		if self.doc.docstatus == 1:
			# calculate transferred qty based on submitted stock entries
			self.update_transferred_qty_for_required_items()

			# update in bin
			self.update_reserved_qty_for_production()

		StockReservationService(self.doc).validate_reserved_qty()

	def update_reserved_qty_for_production(self, items=None):
		"""update reserved_qty_for_production in bins"""
		for d in self.doc.required_items:
			if d.source_warehouse:
				stock_bin = get_bin(d.item_code, d.source_warehouse)
				stock_bin.update_reserved_qty_for_production()

	def get_items_and_operations_from_bom(self):
		self.set_required_items()
		self.doc.set_work_order_operations()

		return check_if_scrap_warehouse_mandatory(self.doc.bom_no)

	def set_available_qty(self):
		for d in self.doc.get("required_items"):
			if d.source_warehouse:
				d.available_qty_at_source_warehouse = get_latest_stock_qty(d.item_code, d.source_warehouse)

			if self.doc.wip_warehouse:
				d.available_qty_at_wip_warehouse = get_latest_stock_qty(d.item_code, self.doc.wip_warehouse)

	def set_required_items(self, reset_only_qty=False, reset_source_warehouse=False):
		"""set required_items for production to keep track of reserved qty"""
		if not reset_only_qty:
			self.doc.required_items = []

		if not (self.doc.bom_no and self.doc.qty):
			return

		operations = self.doc.get("operations") or []
		operation = operations[0].operation if len(operations) == 1 else None
		item_dict = get_bom_items_as_dict(
			self.doc.bom_no, self.doc.company, qty=self.doc.qty, fetch_exploded=self.doc.use_multi_level_bom
		)

		if reset_only_qty:
			self._reset_required_qty(item_dict, operation)
		else:
			self._append_required_items(item_dict, operation, reset_source_warehouse)
		self.set_available_qty()

	def _reset_required_qty(self, item_dict, operation):
		for d in self.doc.get("required_items"):
			if item_dict.get(d.item_code):
				d.required_qty = item_dict.get(d.item_code).get("qty")

			if not d.operation:
				d.operation = operation

	def _append_required_items(self, item_dict, operation, reset_source_warehouse):
		for item in sorted(item_dict.values(), key=lambda d: d["idx"] or float("inf")):
			source_warehouse = self._item_source_warehouse(item, reset_source_warehouse)
			self.doc.append("required_items", self._required_item_row(item, operation, source_warehouse))

			if self.doc.subcontracting_inward_order and not frappe.get_cached_value(
				"Item", item.item_code, "is_customer_provided_item"
			):
				self.doc.required_items[-1].source_warehouse = item.default_warehouse

			if not self.doc.project:
				self.doc.project = item.get("project")

	def _item_source_warehouse(self, item, reset_source_warehouse):
		if reset_source_warehouse:
			return self.doc.source_warehouse
		return self.doc.source_warehouse or item.source_warehouse or item.default_warehouse

	def _required_item_row(self, item, operation, source_warehouse):
		return {
			"rate": item.rate,
			"amount": item.rate * item.qty,
			"operation": item.operation or operation,
			"item_code": item.item_code,
			"item_name": item.item_name,
			"stock_uom": item.stock_uom,
			"description": item.description,
			"allow_alternative_item": item.allow_alternative_item,
			"required_qty": item.qty,
			"source_warehouse": source_warehouse,
			"include_item_in_manufacturing": item.include_item_in_manufacturing,
			"operation_row_id": item.operation_row_id,
		}

	def update_transferred_qty_for_required_items(self):
		if self.doc.skip_transfer:
			return

		transferred_items = self._material_transfer_qty_by_item(is_return=0)
		row_wise_serial_batch = frappe._dict({})
		if self.doc.reserve_stock:
			row_wise_serial_batch = get_row_wise_serial_batch(self.doc.name)

		for row in self.doc.required_items:
			transferred_qty = transferred_items.get(row.item_code) or 0.0
			row.db_set("transferred_qty", transferred_qty, update_modified=False)
			if self.doc.reserve_stock:
				StockReservationService(self.doc).update_qty_in_stock_reservation(
					row, transferred_qty, row_wise_serial_batch
				)

	def update_returned_qty(self):
		returned_dict = self._material_transfer_qty_by_item(is_return=1)
		for row in self.doc.required_items:
			row.db_set("returned_qty", (returned_dict.get(row.item_code) or 0.0), update_modified=False)

	def _material_transfer_qty_by_item(self, is_return):
		ste = frappe.qb.DocType("Stock Entry")
		ste_child = frappe.qb.DocType("Stock Entry Detail")
		query = (
			frappe.qb.from_(ste)
			.inner_join(ste_child)
			.on(ste_child.parent == ste.name)
			.select(ste_child.item_code, ste_child.original_item, fn.Sum(ste_child.transfer_qty).as_("qty"))
			.where(self._material_transfer_filter(ste, is_return))
			.groupby(ste_child.item_code)
		)
		return frappe._dict({d.original_item or d.item_code: d.qty for d in (query.run(as_dict=1) or [])})

	def _material_transfer_filter(self, ste, is_return):
		return (
			(ste.docstatus == 1)
			& (ste.work_order == self.doc.name)
			& (ste.purpose == "Material Transfer for Manufacture")
			& (ste.is_return == is_return)
		)

	def update_consumed_qty_for_required_items(self):
		"""
		Update consumed qty from submitted stock entries
		against a work order for each stock item
		"""
		wip_warehouse = self.doc.wip_warehouse
		if self.doc.skip_transfer and not self.doc.from_wip_warehouse:
			wip_warehouse = None

		for item in self.doc.required_items:
			consumed_qty = get_consumed_qty(self.doc.name, item.item_code) + item.returned_qty
			item.db_set("consumed_qty", flt(consumed_qty), update_modified=False)

			if not self.doc.reserve_stock:
				continue

			warehouse = wip_warehouse or item.source_warehouse
			StockReservationService(self.doc).update_consumed_qty_in_stock_reservation(
				item, consumed_qty, warehouse
			)

	def remove_additional_items(self, stock_entry):
		for row in stock_entry.items:
			for item in self.doc.required_items:
				if row.item_code == item.item_code and row.name == item.voucher_detail_reference:
					item.delete()

	def add_additional_items(self, stock_entry):
		if frappe.db.get_single_value("Manufacturing Settings", "validate_components_quantities_per_bom"):
			return

		if stock_entry.purpose != "Material Transfer for Manufacture":
			return

		additional_items = self._additional_items_by_code(stock_entry)
		self.doc.flags.ignore_validate_update_after_submit = True
		for rows in additional_items.values():
			for row in rows:
				self.doc.append("required_items", self._additional_item_row(row))

		self.doc.save()
		stock_entry.reload()

	def _additional_items_by_code(self, stock_entry):
		required_items = [d.item_code for d in self.doc.required_items]
		additional_items = frappe._dict()
		for row in stock_entry.items:
			item_code = row.original_item if row.original_item else row.item_code
			if item_code not in required_items:
				additional_items.setdefault(item_code, []).append(row)
		return additional_items

	@staticmethod
	def _additional_item_row(row):
		return {
			"item_code": row.original_item or row.item_code,
			"source_warehouse": row.s_warehouse,
			"item_name": row.item_name,
			"required_qty": row.transfer_qty,
			"stock_uom": row.stock_uom,
			"rate": row.basic_rate,
			"amount": row.amount,
			"description": row.description,
			"is_additional_item": 1,
			"voucher_detail_reference": row.name,
		}

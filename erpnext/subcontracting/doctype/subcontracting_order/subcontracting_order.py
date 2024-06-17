# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext.buying.doctype.purchase_order.purchase_order import is_subcontracting_order_created
from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.stock.stock_balance import update_bin_qty
from erpnext.stock.utils import get_bin


class SubcontractingOrder(SubcontractingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.landed_cost_taxes_and_charges.landed_cost_taxes_and_charges import (
			LandedCostTaxesandCharges,
		)
		from erpnext.subcontracting.doctype.subcontracting_order_item.subcontracting_order_item import (
			SubcontractingOrderItem,
		)
		from erpnext.subcontracting.doctype.subcontracting_order_service_item.subcontracting_order_service_item import (
			SubcontractingOrderServiceItem,
		)
		from erpnext.subcontracting.doctype.subcontracting_order_supplied_item.subcontracting_order_supplied_item import (
			SubcontractingOrderSuppliedItem,
		)

		additional_costs: DF.Table[LandedCostTaxesandCharges]
		address_display: DF.SmallText | None
		amended_from: DF.Link | None
		billing_address: DF.Link | None
		billing_address_display: DF.SmallText | None
		company: DF.Link
		contact_display: DF.SmallText | None
		contact_email: DF.SmallText | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		cost_center: DF.Link | None
		distribute_additional_costs_based_on: DF.Literal["Qty", "Amount"]
		items: DF.Table[SubcontractingOrderItem]
		letter_head: DF.Link | None
		naming_series: DF.Literal["SC-ORD-.YYYY.-"]
		per_received: DF.Percent
		project: DF.Link | None
		purchase_order: DF.Link
		schedule_date: DF.Date | None
		select_print_heading: DF.Link | None
		service_items: DF.Table[SubcontractingOrderServiceItem]
		set_reserve_warehouse: DF.Link | None
		set_warehouse: DF.Link | None
		shipping_address: DF.Link | None
		shipping_address_display: DF.SmallText | None
		status: DF.Literal[
			"Draft",
			"Open",
			"Partially Received",
			"Completed",
			"Material Transferred",
			"Partial Material Transferred",
			"Cancelled",
			"Closed",
		]
		supplied_items: DF.Table[SubcontractingOrderSuppliedItem]
		supplier: DF.Link
		supplier_address: DF.Link | None
		supplier_name: DF.Data
		supplier_warehouse: DF.Link
		title: DF.Data | None
		total: DF.Currency
		total_additional_costs: DF.Currency
		total_qty: DF.Float
		transaction_date: DF.Date
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.status_updater = [
			{
				"source_dt": "Subcontracting Order Item",
				"target_dt": "Material Request Item",
				"join_field": "material_request_item",
				"target_field": "ordered_qty",
				"target_parent_dt": "Material Request",
				"target_parent_field": "per_ordered",
				"target_ref_field": "stock_qty",
				"source_field": "qty",
				"percent_join_field": "material_request",
			}
		]

	def onload(self):
		self.set_onload(
			"over_transfer_allowance",
			frappe.db.get_single_value("Buying Settings", "over_transfer_allowance"),
		)

	def before_validate(self):
		super().before_validate()

	def validate(self):
		super().validate()
		self.validate_purchase_order_for_subcontracting()
		self.validate_items()
		self.validate_service_items()
		self.validate_supplied_items()
		self.set_missing_values()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def on_submit(self):
		self.update_prevdoc_status()
		self.update_status()

	def on_cancel(self):
		self.update_prevdoc_status()
		self.update_status()

	def validate_purchase_order_for_subcontracting(self):
		if self.purchase_order:
			if is_subcontracting_order_created(self.purchase_order):
				frappe.throw(
					_(
						"Only one Subcontracting Order can be created against a Purchase Order, cancel the existing Subcontracting Order to create a new one."
					)
				)

			po = frappe.get_doc("Purchase Order", self.purchase_order)

			if not po.is_subcontracted:
				frappe.throw(_("Please select a valid Purchase Order that is configured for Subcontracting."))

			if po.is_old_subcontracting_flow:
				frappe.throw(_("Please select a valid Purchase Order that has Service Items."))

			if po.docstatus != 1:
				msg = f"Please submit Purchase Order {po.name} before proceeding."
				frappe.throw(_(msg))

			if po.per_received == 100:
				msg = f"Cannot create more Subcontracting Orders against the Purchase Order {po.name}."
				frappe.throw(_(msg))
		else:
			self.service_items = self.items = self.supplied_items = None
			frappe.throw(_("Please select a Subcontracting Purchase Order."))

	def validate_service_items(self):
		for item in self.service_items:
			if frappe.get_value("Item", item.item_code, "is_stock_item"):
				msg = f"Service Item {item.item_name} must be a non-stock item."
				frappe.throw(_(msg))

	def validate_supplied_items(self):
		if self.supplier_warehouse:
			for item in self.supplied_items:
				if self.supplier_warehouse == item.reserve_warehouse:
					msg = f"Reserve Warehouse must be different from Supplier Warehouse for Supplied Item {item.main_item_code}."
					frappe.throw(_(msg))

	def set_missing_values(self):
		self.calculate_additional_costs()
		self.calculate_service_costs()
		self.calculate_supplied_items_qty_and_amount()
		self.calculate_items_qty_and_amount()

	def calculate_service_costs(self):
		for idx, item in enumerate(self.get("service_items")):
			self.items[idx].service_cost_per_qty = item.amount / self.items[idx].qty

	def calculate_supplied_items_qty_and_amount(self):
		for item in self.get("items"):
			bom = frappe.get_doc("BOM", item.bom)
			rm_cost = sum(flt(rm_item.amount) for rm_item in bom.items)
			item.rm_cost_per_qty = rm_cost / flt(bom.quantity)

	def calculate_items_qty_and_amount(self):
		total_qty = total = 0
		for item in self.items:
			item.rate = item.rm_cost_per_qty + item.service_cost_per_qty + flt(item.additional_cost_per_qty)
			item.amount = item.qty * item.rate
			total_qty += flt(item.qty)
			total += flt(item.amount)
		else:
			self.total_qty = total_qty
			self.total = total

	def update_ordered_qty_for_subcontracting(self, sco_item_rows=None):
		item_wh_list = []
		for item in self.get("items"):
			if (
				(not sco_item_rows or item.name in sco_item_rows)
				and [item.item_code, item.warehouse] not in item_wh_list
				and frappe.get_cached_value("Item", item.item_code, "is_stock_item")
				and item.warehouse
			):
				item_wh_list.append([item.item_code, item.warehouse])
		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {"ordered_qty": self.get_ordered_qty(item_code, warehouse)})

	@staticmethod
	def get_ordered_qty(item_code, warehouse):
		table = frappe.qb.DocType("Subcontracting Order")
		child = frappe.qb.DocType("Subcontracting Order Item")

		query = (
			frappe.qb.from_(table)
			.inner_join(child)
			.on(table.name == child.parent)
			.select((child.qty - child.received_qty) * child.conversion_factor)
			.where(
				(table.docstatus == 1)
				& (child.item_code == item_code)
				& (child.warehouse == warehouse)
				& (child.qty > child.received_qty)
				& (table.status != "Completed")
			)
		)

		query = query.run()

		return flt(query[0][0]) if query else 0

	def update_reserved_qty_for_subcontracting(self):
		for item in self.supplied_items:
			if item.rm_item_code:
				stock_bin = get_bin(item.rm_item_code, item.reserve_warehouse)
				stock_bin.update_reserved_qty_for_sub_contracting()

	def populate_items_table(self):
		items = []

		for si in self.service_items:
			if si.fg_item:
				item = frappe.get_doc("Item", si.fg_item)
				bom = (
					frappe.db.get_value(
						"Subcontracting BOM",
						{"finished_good": item.item_code, "is_active": 1},
						"finished_good_bom",
					)
					or item.default_bom
				)

				items.append(
					{
						"item_code": item.item_code,
						"item_name": item.item_name,
						"schedule_date": self.schedule_date,
						"description": item.description,
						"qty": si.fg_item_qty,
						"stock_uom": item.stock_uom,
						"bom": bom,
						"purchase_order_item": si.purchase_order_item,
						"material_request": si.material_request,
						"material_request_item": si.material_request_item,
					}
				)
			else:
				frappe.throw(
					_("Please select Finished Good Item for Service Item {0}").format(
						si.item_name or si.item_code
					)
				)

		if items:
			for item in items:
				self.append("items", item)

		self.set_missing_values()

	def update_status(self, status=None, update_modified=True):
		if self.status == "Closed" and self.status != status:
			check_on_hold_or_closed_status("Purchase Order", self.purchase_order)

		if self.docstatus >= 1 and not status:
			if self.docstatus == 1:
				if self.status == "Draft":
					status = "Open"
				elif self.per_received >= 100:
					status = "Completed"
				elif self.per_received > 0 and self.per_received < 100:
					status = "Partially Received"
				else:
					total_required_qty = total_supplied_qty = 0
					for item in self.supplied_items:
						total_required_qty += item.required_qty
						total_supplied_qty += flt(item.supplied_qty)
					if total_supplied_qty:
						status = "Partial Material Transferred"
						if total_supplied_qty >= total_required_qty:
							status = "Material Transferred"
					else:
						status = "Open"
			elif self.docstatus == 2:
				status = "Cancelled"

		if status and self.status != status:
			self.db_set("status", status, update_modified=update_modified)

		self.update_requested_qty()
		self.update_ordered_qty_for_subcontracting()
		self.update_reserved_qty_for_subcontracting()


@frappe.whitelist()
def make_subcontracting_receipt(source_name, target_doc=None):
	return get_mapped_subcontracting_receipt(source_name, target_doc)


def get_mapped_subcontracting_receipt(source_name, target_doc=None):
	def update_item(source, target, source_parent):
		target.purchase_order = source_parent.purchase_order
		target.purchase_order_item = source.purchase_order_item
		target.qty = flt(source.qty) - flt(source.received_qty)
		target.amount = (flt(source.qty) - flt(source.received_qty)) * flt(source.rate)

	target_doc = get_mapped_doc(
		"Subcontracting Order",
		source_name,
		{
			"Subcontracting Order": {
				"doctype": "Subcontracting Receipt",
				"field_map": {
					"supplier_warehouse": "supplier_warehouse",
					"set_warehouse": "set_warehouse",
				},
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Subcontracting Order Item": {
				"doctype": "Subcontracting Receipt Item",
				"field_map": {
					"name": "subcontracting_order_item",
					"parent": "subcontracting_order",
					"bom": "bom",
				},
				"postprocess": update_item,
				"condition": lambda doc: abs(doc.received_qty) < abs(doc.qty),
			},
		},
		target_doc,
	)

	return target_doc


@frappe.whitelist()
def update_subcontracting_order_status(sco, status=None):
	if isinstance(sco, str):
		sco = frappe.get_doc("Subcontracting Order", sco)

	sco.update_status(status)

# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	StockReservation,
	has_reserved_stock,
)
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
		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		billing_address: DF.Link | None
		billing_address_display: DF.TextEditor | None
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
		production_plan: DF.Data | None
		project: DF.Link | None
		purchase_order: DF.Link
		reserve_stock: DF.Check
		schedule_date: DF.Date | None
		select_print_heading: DF.Link | None
		service_items: DF.Table[SubcontractingOrderServiceItem]
		set_reserve_warehouse: DF.Link | None
		set_warehouse: DF.Link | None
		shipping_address: DF.Link | None
		shipping_address_display: DF.TextEditor | None
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
		supplier_currency: DF.Link | None
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

		if self.reserve_stock:
			if self.has_unreserved_stock():
				self.set_onload("has_unreserved_stock", True)

			if has_reserved_stock(self.doctype, self.name):
				self.set_onload("has_reserved_stock", True)

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
		self.update_subcontracted_quantity_in_po()
		self.reserve_raw_materials()

	def on_cancel(self):
		self.update_prevdoc_status()
		self.update_status()
		self.update_subcontracted_quantity_in_po(cancel=True)

	def validate_purchase_order_for_subcontracting(self):
		if self.purchase_order:
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
		purchase_order_items = [item.purchase_order_item for item in self.items]
		self.service_items = [
			service_item
			for service_item in self.service_items
			if service_item.purchase_order_item in purchase_order_items
		]

		for service_item in self.service_items:
			if frappe.get_value("Item", service_item.item_code, "is_stock_item"):
				frappe.throw(_("Service Item {0} must be a non-stock item.").format(service_item.item_code))

			item = next(
				item for item in self.items if item.purchase_order_item == service_item.purchase_order_item
			)
			service_item.qty = item.qty * item.subcontracting_conversion_factor
			service_item.fg_item_qty = item.qty
			service_item.amount = service_item.qty * service_item.rate

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
			item.rm_cost_per_qty = flt(rm_cost / flt(bom.quantity), item.precision("rm_cost_per_qty"))

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

	def update_reserved_qty_for_subcontracting(self, sco_item_rows=None):
		for item in self.supplied_items:
			if sco_item_rows and item.reference_name not in sco_item_rows:
				continue

			if item.rm_item_code:
				stock_bin = get_bin(item.rm_item_code, item.reserve_warehouse)
				stock_bin.update_reserved_qty_for_sub_contracting()

	def populate_items_table(self):
		items = []

		for si in self.service_items:
			if si.fg_item:
				item = frappe.get_doc("Item", si.fg_item)

				qty, subcontracted_qty, fg_item_qty, production_plan_sub_assembly_item = frappe.db.get_value(
					"Purchase Order Item",
					si.purchase_order_item,
					["qty", "subcontracted_qty", "fg_item_qty", "production_plan_sub_assembly_item"],
				)
				available_qty = flt(qty) - flt(subcontracted_qty)

				if available_qty == 0:
					continue

				si.qty = available_qty
				conversion_factor = flt(qty) / flt(fg_item_qty)
				si.fg_item_qty = flt(
					available_qty / conversion_factor, frappe.get_precision("Purchase Order Item", "qty")
				)
				si.amount = available_qty * si.rate

				bom = (
					frappe.db.get_value(
						"Subcontracting BOM",
						{"finished_good": item.name, "is_active": 1},
						"finished_good_bom",
					)
					or item.default_bom
				)

				items.append(
					{
						"item_code": item.name,
						"item_name": item.item_name,
						"schedule_date": self.schedule_date,
						"description": item.description,
						"qty": si.fg_item_qty,
						"subcontracting_conversion_factor": conversion_factor,
						"stock_uom": item.stock_uom,
						"bom": bom,
						"purchase_order_item": si.purchase_order_item,
						"material_request": si.material_request,
						"material_request_item": si.material_request_item,
						"production_plan_sub_assembly_item": production_plan_sub_assembly_item,
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

	def update_status(self, status=None, update_modified=True, update_bin=True):
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
		if update_bin:
			self.update_ordered_qty_for_subcontracting()
			self.update_reserved_qty_for_subcontracting()

	def update_subcontracted_quantity_in_po(self, cancel=False):
		for service_item in self.service_items:
			subcontracted_qty = flt(
				frappe.db.get_value(
					"Purchase Order Item", service_item.purchase_order_item, "subcontracted_qty"
				)
			)

			subcontracted_qty = (
				(subcontracted_qty + service_item.qty)
				if not cancel
				else (subcontracted_qty - service_item.qty)
			)

			frappe.db.set_value(
				"Purchase Order Item",
				service_item.purchase_order_item,
				"subcontracted_qty",
				subcontracted_qty,
			)

	@frappe.whitelist()
	def reserve_raw_materials(self, items=None, stock_entry=None):
		if self.reserve_stock:
			item_dict = {}

			if items:
				item_dict = {d["name"]: d for d in items}
				items = [item for item in self.supplied_items if item.name in item_dict]

			reservation_items = []
			is_transfer = False
			for item in items or self.supplied_items:
				data = frappe._dict(
					{
						"voucher_no": self.name,
						"voucher_type": self.doctype,
						"voucher_detail_no": item.name,
						"item_code": item.rm_item_code,
						"warehouse": item_dict.get(item.name, {}).get("warehouse", item.reserve_warehouse),
						"stock_qty": item_dict.get(item.name, {}).get("qty_to_reserve", item.required_qty),
					}
				)

				if stock_entry:
					data.update(
						{
							"from_voucher_no": stock_entry,
							"from_voucher_type": "Stock Entry",
							"from_voucher_detail_no": item_dict[item.name]["reference_voucher_detail_no"],
							"serial_and_batch_bundles": item_dict[item.name]["serial_and_batch_bundles"],
						}
					)
				elif self.production_plan:
					fg_item = next(i for i in self.items if i.name == item.reference_name)
					if production_plan_sub_assembly_item := fg_item.production_plan_sub_assembly_item:
						from_voucher_detail_no, reserved_qty = frappe.get_value(
							"Material Request Plan Item",
							{
								"parent": self.production_plan,
								"item_code": item.rm_item_code,
								"warehouse": item.reserve_warehouse,
								"sub_assembly_item_reference": production_plan_sub_assembly_item,
								"docstatus": 1,
							},
							["name", "stock_reserved_qty"],
						)
						if flt(item.stock_reserved_qty) < reserved_qty:
							is_transfer = True
							data.update(
								{
									"from_voucher_no": self.production_plan,
									"from_voucher_type": "Production Plan",
									"from_voucher_detail_no": from_voucher_detail_no,
								}
							)

				reservation_items.append(data)

			sre = StockReservation(self, items=reservation_items, notify=True)
			if is_transfer:
				sre.transfer_reservation_entries_to(
					self.production_plan, from_doctype="Production Plan", to_doctype="Subcontracting Order"
				)
			else:
				if sre.make_stock_reservation_entries():
					frappe.msgprint(_("Stock Reservation Entries created"), alert=True, indicator="blue")

	def has_unreserved_stock(self) -> bool:
		for item in self.get("supplied_items"):
			if item.required_qty - flt(item.supplied_qty) - flt(item.stock_reserved_qty) > 0:
				return True

		return False

	@frappe.whitelist()
	def cancel_stock_reservation_entries(self, sre_list=None, notify=True) -> None:
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)

		cancel_stock_reservation_entries(
			voucher_type=self.doctype, voucher_no=self.name, sre_list=sre_list, notify=notify
		)


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

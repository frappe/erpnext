# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import comma_and, flt, get_link_to_form

from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.controllers.subcontracting_controller import SubcontractingController


class SubcontractingInwardOrder(SubcontractingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.subcontracting.doctype.subcontracting_inward_order_item.subcontracting_inward_order_item import (
			SubcontractingInwardOrderItem,
		)
		from erpnext.subcontracting.doctype.subcontracting_inward_order_received_item.subcontracting_inward_order_received_item import (
			SubcontractingInwardOrderReceivedItem,
		)
		from erpnext.subcontracting.doctype.subcontracting_inward_order_scrap_item.subcontracting_inward_order_scrap_item import (
			SubcontractingInwardOrderScrapItem,
		)
		from erpnext.subcontracting.doctype.subcontracting_inward_order_service_item.subcontracting_inward_order_service_item import (
			SubcontractingInwardOrderServiceItem,
		)

		amended_from: DF.Link | None
		company: DF.Link
		currency: DF.Link | None
		customer: DF.Link
		customer_name: DF.Data
		customer_warehouse: DF.Link
		items: DF.Table[SubcontractingInwardOrderItem]
		naming_series: DF.Literal["SCI-ORD-.YYYY.-"]
		per_delivered: DF.Percent
		per_process_loss: DF.Percent
		per_produced: DF.Percent
		per_raw_material_received: DF.Percent
		per_raw_material_returned: DF.Percent
		per_returned: DF.Percent
		received_items: DF.Table[SubcontractingInwardOrderReceivedItem]
		sales_order: DF.Link
		scrap_items: DF.Table[SubcontractingInwardOrderScrapItem]
		service_items: DF.Table[SubcontractingInwardOrderServiceItem]
		set_delivery_warehouse: DF.Link | None
		status: DF.Literal["Draft", "Open", "Ongoing", "Produced", "Delivered", "Cancelled", "Closed"]
		title: DF.Data | None
		transaction_date: DF.Date
	# end: auto-generated types

	pass

	def validate(self):
		super().validate()
		self.set_is_customer_provided_item()
		self.validate_customer_provided_items()
		self.validate_customer_warehouse()
		self.validate_service_items()
		self.set_missing_values()

	def on_submit(self):
		self.update_status()
		self.update_subcontracted_quantity_in_so()

	def on_cancel(self):
		self.update_status()
		self.update_subcontracted_quantity_in_so()

	def update_status(self, status=None, update_modified=True):
		if self.status == "Closed" and self.status != status:
			check_on_hold_or_closed_status("Sales Order", self.sales_order)

		total_to_be_received = total_received = total_rm_returned = 0
		for rm in self.get("received_items"):
			if rm.get("is_customer_provided_item"):
				total_to_be_received += flt(rm.required_qty)
				total_received += flt(rm.received_qty)
				total_rm_returned += flt(rm.returned_qty)

		total_to_be_produced = total_produced = total_process_loss = total_delivered = total_fg_returned = 0
		for item in self.get("items"):
			total_to_be_produced += flt(item.qty)
			total_produced += flt(item.produced_qty)
			total_process_loss += flt(item.process_loss_qty)
			total_delivered += flt(item.delivered_qty)
			total_fg_returned += flt(item.returned_qty)

		per_raw_material_received = flt(total_received / total_to_be_received * 100, 2)
		per_raw_material_returned = flt(total_rm_returned / total_received * 100, 2) if total_received else 0
		per_produced = flt(total_produced / total_to_be_produced * 100, 2)
		per_process_loss = flt(total_process_loss / total_produced * 100, 2) if total_produced else 0
		per_delivered = flt(total_delivered / total_to_be_produced * 100, 2)
		per_returned = flt(total_fg_returned / total_delivered * 100, 2) if total_delivered else 0

		self.db_set("per_raw_material_received", per_raw_material_received, update_modified=update_modified)
		self.db_set("per_raw_material_returned", per_raw_material_returned, update_modified=update_modified)
		self.db_set("per_produced", per_produced, update_modified=update_modified)
		self.db_set("per_process_loss", per_process_loss, update_modified=update_modified)
		self.db_set("per_delivered", per_delivered, update_modified=update_modified)
		self.db_set("per_returned", per_returned, update_modified=update_modified)

		if self.docstatus >= 1 and not status:
			if self.docstatus == 1:
				if self.status == "Draft":
					status = "Open"
				elif self.per_delivered == 100:
					status = "Delivered"
				elif self.per_produced == 100:
					status = "Produced"
				elif self.per_raw_material_received > 0:
					status = "Ongoing"
				else:
					status = "Open"
			elif self.docstatus == 2:
				status = "Cancelled"

		if status and self.status != status:
			self.db_set("status", status, update_modified=update_modified)

	def update_subcontracted_quantity_in_so(self):
		for service_item in self.service_items:
			doc = frappe.get_doc("Sales Order Item", service_item.sales_order_item)
			doc.subcontracted_qty = (
				(doc.subcontracted_qty + service_item.qty)
				if self._action == "submit"
				else (doc.subcontracted_qty - service_item.qty)
			)
			doc.save()

	def validate_customer_warehouse(self):
		if frappe.get_cached_value("Warehouse", self.customer_warehouse, "customer") != self.customer:
			frappe.throw(
				_("Customer Warehouse {0} does not belong to Customer {1}.").format(
					frappe.bold(self.customer_warehouse), frappe.bold(self.customer)
				)
			)

	def validate_service_items(self):
		sales_order_items = [item.sales_order_item for item in self.items]
		self.service_items = [
			service_item
			for service_item in self.service_items
			if service_item.sales_order_item in sales_order_items
		]

		for service_item in self.service_items:
			item = next(item for item in self.items if item.sales_order_item == service_item.sales_order_item)
			service_item.qty = item.qty * item.subcontracting_conversion_factor
			service_item.fg_item_qty = item.qty
			service_item.amount = service_item.qty * service_item.rate

	def populate_items_table(self):
		items = []

		for si in self.service_items:
			if si.fg_item:
				item = frappe.get_doc("Item", si.fg_item)

				so_item = frappe.get_doc("Sales Order Item", si.sales_order_item)
				available_qty = so_item.stock_qty - so_item.subcontracted_qty

				if available_qty == 0:
					continue

				si.required_qty = available_qty
				conversion_factor = so_item.stock_qty / so_item.fg_item_qty
				si.fg_item_qty = flt(
					available_qty / conversion_factor, frappe.get_precision("Sales Order Item", "qty")
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
						"expected_delivery_date": frappe.get_cached_value(
							"Sales Order Item", si.sales_order_item, "delivery_date"
						),
						"description": item.description,
						"qty": si.fg_item_qty,
						"subcontracting_conversion_factor": conversion_factor,
						"stock_uom": item.stock_uom,
						"bom": bom,
						"sales_order_item": si.sales_order_item,
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

	def validate_customer_provided_items(self):
		"""Check if atleast one raw material is customer provided"""
		for item in self.get("items"):
			raw_materials = [rm for rm in self.get("received_items") if rm.main_item_code == item.item_code]
			if not any([rm.is_customer_provided_item for rm in raw_materials]):
				frappe.throw(
					_(
						"Atleast one raw material for Finished Good Item {0} should be customer provided."
					).format(frappe.bold(item.item_code))
				)

	def set_is_customer_provided_item(self):
		for item in self.get("received_items"):
			item.is_customer_provided_item = frappe.get_cached_value(
				"Item", item.rm_item_code, "is_customer_provided_item"
			)

	@frappe.whitelist()
	def make_work_order(self):
		"""Create Work Order from Subcontracting Inward Order."""
		wo_list = []

		for item in self.get_production_items():
			work_order = self.create_work_order(item)
			if work_order:
				wo_list.append(work_order)

		self.show_list_created_message("Work Order", wo_list)

		if not wo_list:
			frappe.msgprint(_("No Work Orders were created"))

		return wo_list

	def get_production_items(self):
		item_list = []

		for d in self.items:
			if d.produced_qty >= d.qty:
				continue

			item_details = {
				"production_item": d.item_code,
				"use_multi_level_bom": d.include_exploded_items,
				"subcontracting_inward_order": self.name,
				"bom_no": d.bom,
				"stock_uom": d.stock_uom,
				"company": self.company,
				"project": frappe.get_cached_value("Sales Order", self.sales_order, "project"),
				"source_warehouse": self.customer_warehouse,
				"subcontracting_inward_order_item": d.name,
				"reserve_stock": 1,
				"fg_warehouse": d.delivery_warehouse,
			}

			qty = min(
				[
					flt(
						(item.received_qty - item.returned_qty - item.work_order_qty)
						/ flt(item.required_qty / d.qty, d.precision("qty")),
						d.precision("qty"),
					)
					for item in self.get("received_items")
					if item.reference_name == d.name and item.is_customer_provided_item and item.required_qty
				]
			)
			qty = min(
				int(qty) if frappe.get_cached_value("UOM", d.stock_uom, "must_be_whole_number") else qty,
				d.qty - d.produced_qty,
			)

			item_details.update({"qty": qty, "max_producible_qty": qty})
			item_list.append(item_details)

		return item_list

	def create_work_order(self, item):
		from erpnext.manufacturing.doctype.work_order.work_order import OverProductionError

		if flt(item.get("qty")) <= 0:
			return

		wo = frappe.new_doc("Work Order")
		wo.update(item)

		wo.set_work_order_operations()
		wo.set_required_items()

		try:
			wo.flags.ignore_mandatory = True
			wo.flags.ignore_validate = True
			wo.insert()
			return wo.name
		except OverProductionError:
			pass

	def show_list_created_message(self, doctype, doc_list=None):
		if not doc_list:
			return

		frappe.flags.mute_messages = False
		if doc_list:
			doc_list = [get_link_to_form(doctype, p) for p in doc_list]
			frappe.msgprint(_("{0} created").format(comma_and(doc_list)))

	@frappe.whitelist()
	def make_rm_stock_entry_inward(self, target_doc=None):
		def calculate_qty_as_per_bom(rm_item):
			data = frappe.get_value(
				"Subcontracting Inward Order Item",
				{"name": rm_item.reference_name},
				["process_loss_qty", "include_exploded_items"],
				as_dict=True,
			)
			stock_qty = frappe.get_value(
				"BOM Explosion Item" if data.include_exploded_items else "BOM Item",
				{"name": rm_item.bom_detail_no},
				"stock_qty",
			)
			qty = flt(
				stock_qty * data.process_loss_qty,
				frappe.get_precision("Subcontracting Inward Order Received Item", "required_qty"),
			)
			return rm_item.required_qty - rm_item.received_qty + rm_item.returned_qty + qty

		if target_doc and target_doc.get("items"):
			target_doc.items = []

		stock_entry = get_mapped_doc(
			"Subcontracting Inward Order",
			self.name,
			{
				"Subcontracting Inward Order": {
					"doctype": "Stock Entry",
					"validation": {
						"docstatus": ["=", 1],
					},
				},
			},
			target_doc,
			ignore_child_tables=True,
		)

		stock_entry.purpose = "Receive from Customer"
		stock_entry.subcontracting_inward_order = self.name

		stock_entry.set_stock_entry_type()

		for rm_item in self.received_items:
			if not rm_item.required_qty or not rm_item.is_customer_provided_item:
				continue

			items_dict = {
				rm_item.get("rm_item_code"): {
					"scio_detail": rm_item.get("name"),
					"qty": calculate_qty_as_per_bom(rm_item),
					"to_warehouse": rm_item.get("warehouse"),
					"stock_uom": rm_item.get("stock_uom"),
				}
			}

			stock_entry.add_to_stock_entry_detail(items_dict)

		if target_doc:
			return stock_entry
		else:
			return stock_entry.as_dict()

	@frappe.whitelist()
	def make_rm_return(self, target_doc=None):
		if target_doc and target_doc.get("items"):
			target_doc.items = []

		stock_entry = get_mapped_doc(
			"Subcontracting Inward Order",
			self.name,
			{
				"Subcontracting Inward Order": {
					"doctype": "Stock Entry",
					"validation": {
						"docstatus": ["=", 1],
					},
				},
			},
			target_doc,
			ignore_child_tables=True,
		)

		stock_entry.purpose = "Return Raw Material to Customer"
		stock_entry.set_stock_entry_type()
		stock_entry.subcontracting_inward_order = self.name

		for rm_item in self.received_items:
			items_dict = {
				rm_item.get("rm_item_code"): {
					"scio_detail": rm_item.get("name"),
					"qty": rm_item.received_qty - rm_item.work_order_qty - rm_item.returned_qty,
					"from_warehouse": rm_item.get("warehouse"),
					"stock_uom": rm_item.get("stock_uom"),
				}
			}

			stock_entry.add_to_stock_entry_detail(items_dict)

		if target_doc:
			return stock_entry
		else:
			return stock_entry.as_dict()

	@frappe.whitelist()
	def make_subcontracting_delivery(self, target_doc=None):
		if target_doc and target_doc.get("items"):
			target_doc.items = []

		stock_entry = get_mapped_doc(
			"Subcontracting Inward Order",
			self.name,
			{
				"Subcontracting Inward Order": {
					"doctype": "Stock Entry",
					"validation": {
						"docstatus": ["=", 1],
					},
				},
			},
			target_doc,
			ignore_child_tables=True,
		)

		stock_entry.purpose = "Subcontracting Delivery"
		stock_entry.set_stock_entry_type()
		stock_entry.subcontracting_inward_order = self.name
		scio_details = []

		allow_over = frappe.get_single_value("Selling Settings", "allow_delivery_of_overproduced_qty")
		for fg_item in self.items:
			qty = (
				fg_item.produced_qty
				if allow_over
				else min(fg_item.qty, fg_item.produced_qty) - fg_item.delivered_qty
			)
			if qty < 0:
				continue

			scio_details.append(fg_item.name)
			items_dict = {
				fg_item.item_code: {
					"qty": qty,
					"from_warehouse": fg_item.delivery_warehouse,
					"stock_uom": fg_item.stock_uom,
					"scio_detail": fg_item.name,
					"is_finished_item": 1,
				}
			}

			stock_entry.add_to_stock_entry_detail(items_dict)

		if (
			frappe.get_single_value("Selling Settings", "deliver_scrap_items")
			and self.scrap_items
			and scio_details
		):
			scrap_items = [
				scrap_item for scrap_item in self.scrap_items if scrap_item.reference_name in scio_details
			]
			for scrap_item in scrap_items:
				qty = scrap_item.produced_qty - scrap_item.delivered_qty
				if qty > 0:
					items_dict = {
						scrap_item.item_code: {
							"qty": scrap_item.produced_qty - scrap_item.delivered_qty,
							"from_warehouse": scrap_item.warehouse,
							"stock_uom": scrap_item.stock_uom,
							"scio_detail": scrap_item.name,
							"is_scrap_item": 1,
						}
					}

					stock_entry.add_to_stock_entry_detail(items_dict)

		if target_doc:
			return stock_entry
		else:
			return stock_entry.as_dict()

	@frappe.whitelist()
	def make_subcontracting_return(self, target_doc=None):
		if target_doc and target_doc.get("items"):
			target_doc.items = []

		stock_entry = get_mapped_doc(
			"Subcontracting Inward Order",
			self.name,
			{
				"Subcontracting Inward Order": {
					"doctype": "Stock Entry",
					"validation": {
						"docstatus": ["=", 1],
					},
					"field_map": {"name": "subcontracting_inward_order"},
				},
			},
			target_doc,
			ignore_child_tables=True,
		)

		stock_entry.purpose = "Subcontracting Return"
		stock_entry.set_stock_entry_type()

		for fg_item in self.items:
			qty = fg_item.delivered_qty - fg_item.returned_qty
			if qty < 0:
				continue

			items_dict = {
				fg_item.item_code: {
					"qty": qty,
					"stock_uom": fg_item.stock_uom,
					"scio_detail": fg_item.name,
					"is_finished_item": 1,
				}
			}

			stock_entry.add_to_stock_entry_detail(items_dict)

		if target_doc:
			return stock_entry
		else:
			return stock_entry.as_dict()


@frappe.whitelist()
def update_subcontracting_inward_order_status(scio, status=None):
	if isinstance(scio, str):
		scio = frappe.get_doc("Subcontracting Inward Order", scio)

	scio.update_status(status)

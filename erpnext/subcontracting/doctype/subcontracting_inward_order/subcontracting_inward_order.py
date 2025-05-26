# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe import _
from frappe.utils import comma_and, flt, get_link_to_form

from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.stock.stock_balance import update_bin_qty


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
		from erpnext.subcontracting.doctype.subcontracting_inward_order_service_item.subcontracting_inward_order_service_item import (
			SubcontractingInwardOrderServiceItem,
		)

		amended_from: DF.Link | None
		company: DF.Link
		customer: DF.Link
		customer_name: DF.Data
		items: DF.Table[SubcontractingInwardOrderItem]
		letter_head: DF.Link | None
		naming_series: DF.Literal["SCI-ORD-.YYYY.-"]
		per_delivered: DF.Percent
		per_material_received: DF.Percent
		per_process_loss: DF.Percent
		per_produced: DF.Percent
		per_returned: DF.Percent
		raw_materials_receipt_warehouse: DF.Link
		received_items: DF.Table[SubcontractingInwardOrderReceivedItem]
		sales_order: DF.Link
		select_print_heading: DF.Link | None
		service_items: DF.Table[SubcontractingInwardOrderServiceItem]
		status: DF.Literal["Draft", "Open", "Ongoing", "Produced", "Delivered", "Cancelled", "Closed"]
		title: DF.Data | None
		transaction_date: DF.Date
	# end: auto-generated types

	pass

	def onload(self):
		super().onload()
		if self.docstatus == 1:
			has_unreserved_stock = any(
				[
					item.as_dict().received_qty - item.as_dict().reserved_qty > 0
					for item in self.received_items
				]
			)

			if frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
				if has_unreserved_stock:
					self.set_onload("has_unreserved_stock", True)

				if any([item.as_dict().reserved_qty > 0 for item in self.received_items]):
					self.set_onload("has_reserved_stock", True)

	def before_validate(self):
		super().before_validate()

	def validate(self):
		super().validate()
		self.validate_sales_order_for_subcontracting()
		self.validate_items()
		self.validate_service_items()
		self.set_missing_values()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def on_submit(self):
		self.validate_customer_provided_items()
		self.update_status()
		self.update_subcontracted_quantity_in_so()

	def on_cancel(self):
		self.update_status()
		self.update_subcontracted_quantity_in_so(cancel=True)

	def update_status(self, status=None, update_modified=True):
		if self.status == "Closed" and self.status != status:
			check_on_hold_or_closed_status("Sales Order", self.sales_order)

		total_to_be_received = total_received = 0
		for rm in self.get("received_items"):
			total_to_be_received += rm.required_qty
			total_received += flt(rm.received_qty)

		total_to_be_produced = total_produced = total_process_loss = 0
		for item in self.get("items"):
			total_to_be_produced += item.qty
			total_produced += item.produced_qty
			total_process_loss += item.process_loss_qty

		per_material_received = flt(total_received / total_to_be_received * 100, 2)
		per_produced = flt(total_produced / total_to_be_produced * 100, 2)
		per_process_loss = flt(total_process_loss / total_produced * 100, 2) if total_produced else 0

		self.db_set("per_material_received", per_material_received, update_modified=update_modified)
		self.db_set("per_produced", per_produced, update_modified=update_modified)
		self.db_set("per_process_loss", per_process_loss, update_modified=update_modified)

		if self.docstatus >= 1 and not status:
			if self.docstatus == 1:
				if self.status == "Draft":
					status = "Open"
				elif self.per_produced == 100:
					status = "Produced"
				elif self.per_delivered == 100:
					status = "Delivered"
				elif self.per_material_received > 0:
					status = "Ongoing"
				else:
					status = "Open"
			elif self.docstatus == 2:
				status = "Cancelled"

		if status and self.status != status:
			self.db_set("status", status, update_modified=update_modified)

	def update_subcontracted_quantity_in_so(self, cancel=False):
		for service_item in self.service_items:
			doc = frappe.get_doc("Sales Order Item", service_item.sales_order_item)
			doc.subcontracted_qty = (
				(doc.subcontracted_qty + service_item.qty)
				if not cancel
				else (doc.subcontracted_qty - service_item.qty)
			)
			doc.save()

	def validate_sales_order_for_subcontracting(self):
		if self.sales_order:
			so = frappe.get_doc("Sales Order", self.sales_order)

			if not so.is_subcontracted:
				frappe.throw(_("Please select a valid Sales Order that is configured for Subcontracting."))

			if so.docstatus != 1:
				msg = f"Please submit Sales Order {so.name} before proceeding."
				frappe.throw(_(msg))

			if so.per_delivered == 100:
				msg = f"Cannot create more Subcontracting Inward Orders against the Sales Order {so.name}."
				frappe.throw(_(msg))
		else:
			self.service_items = self.items = self.received_items = None
			frappe.throw(_("Please select a Subcontracted Sales Order."))

	def validate_service_items(self):
		sales_order_items = [item.sales_order_item for item in self.items]
		self.service_items = [
			service_item
			for service_item in self.service_items
			if service_item.sales_order_item in sales_order_items
		]

		for service_item in self.service_items:
			if frappe.get_value("Item", service_item.item_code, "is_stock_item"):
				frappe.throw(_("Service Item {0} must be a non-stock item.").format(service_item.item_code))

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
				available_qty = so_item.qty - so_item.subcontracted_qty

				if available_qty == 0:
					continue

				si.qty = available_qty
				conversion_factor = so_item.qty / so_item.fg_item_qty
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
						"expected_delivery_date": frappe.get_value(
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

		self.set_missing_values()

	def set_missing_values(self):
		self.calculate_service_costs()
		self.set_is_customer_provided_item()  # TODO: Fetch from not working for some reason?

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

	def calculate_additional_costs(self):
		self.total_additional_costs = sum(flt(item.amount) for item in self.get("additional_costs"))

		if self.total_additional_costs:
			if self.distribute_additional_costs_based_on == "Amount":
				total_amt = sum(
					flt(item.amount) for item in self.get("items") if not item.get("is_scrap_item")
				)
				for item in self.items:
					if not item.get("is_scrap_item"):
						item.additional_cost_per_qty = (
							(item.amount * self.total_additional_costs) / total_amt
						) / item.qty
			else:
				total_qty = sum(flt(item.qty) for item in self.get("items") if not item.get("is_scrap_item"))
				additional_cost_per_qty = self.total_additional_costs / total_qty
				for item in self.items:
					if not item.get("is_scrap_item"):
						item.additional_cost_per_qty = additional_cost_per_qty
		else:
			for item in self.items:
				if not item.get("is_scrap_item"):
					item.additional_cost_per_qty = 0

	def calculate_service_costs(self):
		for idx, item in enumerate(self.get("service_items")):
			self.items[idx].service_cost_per_qty = item.amount / self.items[idx].qty

	def set_is_customer_provided_item(self):
		for item in self.get("received_items"):
			item.is_customer_provided_item = frappe.get_value(
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

	def get_production_items(self):
		item_list = []

		for d in self.items:
			if d.produced_qty >= d.qty:
				continue

			item_details = {
				"production_item": d.item_code,
				"use_multi_level_bom": d.include_exploded_items,
				"subcontracting_inward_order": self.name,
				"sales_order": self.sales_order,
				"bom_no": d.bom,
				"stock_uom": d.stock_uom,
				"company": self.company,
				"project": frappe.get_cached_value("Sales Order", self.sales_order, "project"),
				"source_warehouse": self.raw_materials_receipt_warehouse,
				"subcontracting_inward_order_item": d.name,
			}

			qty = min(
				[
					flt(
						(item.received_qty - item.returned_qty - item.work_order_qty)
						/ flt(item.required_qty / d.qty, d.precision("qty")),
						d.precision("qty"),
					)
					for item in self.get("received_items")
					if item.reference_name == d.name
				]
			)

			item_details.update(
				{"qty": int(qty) if frappe.get_value("UOM", d.stock_uom, "must_be_whole_number") else qty}
			)
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
	def create_stock_reservation_entries(
		self,
		items_details: list[dict] | None = None,
		notify=True,
	) -> None:
		"""Creates Stock Reservation Entries for Sales Order Items."""

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			create_stock_reservation_entries_for_scio_rm_items as create_stock_reservation_entries,
		)

		create_stock_reservation_entries(
			scio=self,
			items_details=items_details,
			notify=notify,
		)

	@frappe.whitelist()
	def cancel_stock_reservation_entries(self, sre_list=None, notify=True) -> None:
		"""Cancel Stock Reservation Entries for Sales Order Items."""

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)

		cancel_stock_reservation_entries(
			voucher_type=self.doctype, voucher_no=self.name, sre_list=sre_list, notify=notify
		)


@frappe.whitelist()
def update_subcontracting_inward_order_status(scio, status=None):
	if isinstance(scio, str):
		scio = frappe.get_doc("Subcontracting Inward Order", scio)

	scio.update_status(status)

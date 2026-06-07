# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce, IfNull, Sum
from frappe.utils import (
	cint,
	flt,
	get_link_to_form,
	now,
	nowdate,
)

from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no

# Backward-compatible re-exports: these functions were moved to mapper.py.
# Importing them here preserves existing whitelist dotted-paths
# (e.g. ...work_order.work_order.make_work_order) and external imports.
from erpnext.manufacturing.doctype.work_order.mapper import (
	add_variant_item,
	check_if_scrap_warehouse_mandatory,
	create_job_card,
	create_pick_list,
	get_item_details,
	get_operation_details,
	get_serial_nos_for_job_card,
	get_serial_nos_for_work_order,
	get_template_rm_item,
	get_work_order_operation_data,
	make_job_card,
	make_stock_entry,
	make_stock_return_entry,
	make_work_order,
	split_qty_based_on_batch_size,
	validate_operation_data,
)
from erpnext.manufacturing.doctype.work_order.services.operations import (
	OperationsService,
)
from erpnext.manufacturing.doctype.work_order.services.required_items import (
	RequiredItemsService,
)
from erpnext.manufacturing.doctype.work_order.services.status import (
	StatusService,
)
from erpnext.manufacturing.doctype.work_order.services.stock_reservation import (
	StockReservationService,
	cancel_stock_reservation_entries,
	get_consumed_qty,
	get_reserved_qty_for_production,
	get_row_wise_serial_batch,
	get_sre_details,
	make_stock_reservation_entries,
)
from erpnext.stock.doctype.batch.batch import make_batch
from erpnext.stock.doctype.item.item import validate_end_of_life
from erpnext.stock.doctype.serial_no.serial_no import get_available_serial_nos
from erpnext.stock.utils import validate_warehouse_company
from erpnext.utilities.transaction_base import validate_uom_is_integer


class OverProductionError(frappe.ValidationError):
	pass


class CapacityError(frappe.ValidationError):
	pass


class StockOverProductionError(frappe.ValidationError):
	pass


class OperationTooLongError(frappe.ValidationError):
	pass


class ItemHasVariantError(frappe.ValidationError):
	pass


class SerialNoQtyError(frappe.ValidationError):
	pass


class WorkOrder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.work_order_additional_item.work_order_additional_item import (
			WorkOrderAdditionalItem,
		)
		from erpnext.manufacturing.doctype.work_order_item.work_order_item import WorkOrderItem
		from erpnext.manufacturing.doctype.work_order_operation.work_order_operation import WorkOrderOperation

		actual_end_date: DF.Datetime | None
		actual_operating_cost: DF.Currency
		actual_start_date: DF.Datetime | None
		additional_operating_cost: DF.Currency
		additional_transferred_qty: DF.Float
		allow_alternative_item: DF.Check
		amended_from: DF.Link | None
		batch_size: DF.Float
		bom_no: DF.Link
		company: DF.Link
		corrective_operation_cost: DF.Currency
		description: DF.SmallText | None
		disassembled_qty: DF.Float
		expected_delivery_date: DF.Date | None
		fg_warehouse: DF.Link | None
		from_wip_warehouse: DF.Check
		has_batch_no: DF.Check
		has_serial_no: DF.Check
		image: DF.AttachImage | None
		item_name: DF.Data | None
		lead_time: DF.Float
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		material_transferred_for_manufacturing: DF.Float
		max_producible_qty: DF.Float
		mps: DF.Link | None
		naming_series: DF.Literal["MFG-WO-.YYYY.-"]
		non_stock_items: DF.Table[WorkOrderAdditionalItem]
		operations: DF.Table[WorkOrderOperation]
		planned_end_date: DF.Datetime | None
		planned_operating_cost: DF.Currency
		planned_start_date: DF.Datetime
		process_loss_qty: DF.Float
		produced_qty: DF.Float
		product_bundle_item: DF.Link | None
		production_item: DF.Link
		production_plan: DF.Link | None
		production_plan_item: DF.Data | None
		production_plan_sub_assembly_item: DF.Data | None
		project: DF.Link | None
		qty: DF.Float
		required_items: DF.Table[WorkOrderItem]
		reserve_stock: DF.Check
		sales_order: DF.Link | None
		sales_order_item: DF.Data | None
		scrap_warehouse: DF.Link | None
		secondary_items: DF.Table[WorkOrderAdditionalItem]
		skip_transfer: DF.Check
		source_warehouse: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"Submitted",
			"Not Started",
			"In Process",
			"Stock Reserved",
			"Stock Partially Reserved",
			"Completed",
			"Stopped",
			"Closed",
			"Cancelled",
		]
		stock_uom: DF.Link | None
		subcontracting_inward_order: DF.Link | None
		subcontracting_inward_order_item: DF.Data | None
		total_operating_cost: DF.Currency
		track_semi_finished_goods: DF.Check
		transfer_material_against: DF.Literal["", "Work Order", "Job Card"]
		update_consumed_material_cost_in_project: DF.Check
		use_multi_level_bom: DF.Check
		wip_warehouse: DF.Link | None
	# end: auto-generated types

	def onload(self):
		ms = frappe.get_doc("Manufacturing Settings")
		self.set_onload("allow_editing_items", ms.allow_editing_of_items_and_quantities_in_work_order)
		self.set_onload("material_consumption", ms.material_consumption)
		self.set_onload("backflush_raw_materials_based_on", ms.backflush_raw_materials_based_on)
		self.set_onload("overproduction_percentage", ms.overproduction_percentage_for_work_order)
		self.set_onload("transfer_extra_materials_percentage", ms.transfer_extra_materials_percentage)
		self.set_onload("show_create_job_card_button", self.show_create_job_card_button())
		self.set_onload(
			"enable_stock_reservation",
			frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"),
		)

		if self.bom_no:
			if based_on := frappe.get_cached_value("BOM", self.bom_no, "backflush_based_on"):
				self.set_onload("backflush_raw_materials_based_on", based_on)

	@property
	def secondary_items(self):
		parent = frappe.qb.DocType("Stock Entry")
		child = frappe.qb.DocType("Stock Entry Detail")
		secondary_items_generated = (
			frappe.qb.from_(parent)
			.join(child)
			.on(parent.name == child.parent)
			.where(
				(parent.work_order == self.name)
				& (parent.docstatus == 1)
				& ((child.secondary_item_type != "") | (child.is_legacy_scrap_item == 1))
			)
			.select(
				child.item_code,
				Coalesce(child.secondary_item_type, "Scrap (Legacy)").as_("secondary_item_type"),
				child.qty,
				child.uom,
				child.amount,
			)
			.run(as_dict=True)
		)
		if secondary_items_generated:
			self.set_onload("secondary_items_generated", True)
			return secondary_items_generated
		else:
			secondary_items = frappe.get_query(
				"BOM",
				filters={"name": self.bom_no},
				fields=[
					"secondary_items.item_code",
					"secondary_items.secondary_item_type",
					"secondary_items.qty",
					"secondary_items.uom",
					"secondary_items.cost as amount",
					"quantity as bom_qty",
				],
			).run(as_dict=True)
			secondary_items = [item for item in secondary_items if item.item_code]
			for item in secondary_items:
				item["qty"] = (item.qty / item.bom_qty) * self.qty
				item["amount"] = flt(item.amount) * item.qty
			return secondary_items

	@property
	def non_stock_items(self):
		non_stock_items = frappe.get_query(
			"BOM",
			filters={"name": self.bom_no, "items.is_stock_item": 0, "items.is_phantom_item": 0},
			fields=[
				"items.item_code",
				"items.qty",
				"items.uom",
				"items.base_rate as rate",
				"items.base_amount as amount",
				"quantity as bom_qty",
			],
		).run(as_dict=True)
		for item in non_stock_items:
			item["qty"] = (item.qty / item.bom_qty) * self.qty
			item["amount"] = item.rate * item["qty"]
		return non_stock_items

	def show_create_job_card_button(self):
		jc_doctype = frappe.qb.DocType("Job Card")
		query = (
			frappe.qb.from_(jc_doctype)
			.select(jc_doctype.operation_id, Sum(jc_doctype.for_quantity - IfNull(jc_doctype.pending_qty, 0)))
			.where((jc_doctype.docstatus < 2) & (jc_doctype.work_order == self.name))
			.groupby(jc_doctype.operation_id)
		)

		operation_details = query.run(as_list=1)
		operation_details = frappe._dict(operation_details)

		for d in self.operations:
			job_card_qty = self.qty - flt(operation_details.get(d.name))
			if job_card_qty > 0:
				return True

		return False

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def validate(self):
		self.validate_production_item()
		if self.bom_no:
			validate_bom_no(self.production_item, self.bom_no)

		if not self.subcontracting_inward_order:
			self.validate_sales_order()

		self.set_default_warehouse()
		self.validate_warehouse_belongs_to_company()
		self.check_wip_warehouse_skip()
		self.calculate_operating_cost()
		self.validate_qty()
		self.validate_transfer_against()
		self.validate_operations()
		self.status = self.get_status()
		self.validate_workstation_type()
		self.reset_use_multi_level_bom()
		StockReservationService(self).set_reserve_stock()
		StockReservationService(self).validate_fg_warehouse_for_reservation()
		self.validate_dates()

		if self.source_warehouse:
			self.set_warehouses()

		validate_uom_is_integer(self, "stock_uom", ["required_qty"])

		if not len(self.get("required_items")) or not frappe.db.get_single_value(
			"Manufacturing Settings", "allow_editing_of_items_and_quantities_in_work_order"
		):
			self.set_required_items(reset_only_qty=len(self.get("required_items")))

		StockReservationService(self).enable_auto_reserve_stock()
		self.validate_operations_sequence()
		self.validate_subcontracting_inward_order()

	def validate_dates(self):
		if self.actual_start_date and self.actual_end_date:
			if self.actual_end_date < self.actual_start_date:
				frappe.throw(_("Actual End Date cannot be before Actual Start Date"))

	def before_save(self):
		self.set_skip_transfer_for_operations()

	def set_skip_transfer_for_operations(self):
		if not self.track_semi_finished_goods:
			return

		for op in self.operations:
			op.skip_material_transfer = self.skip_transfer

	def validate_operations_sequence(self):
		if all([not op.sequence_id for op in self.operations]):
			for op in self.operations:
				op.sequence_id = op.idx
		else:
			sequence_id = 1
			for op in self.operations:
				if op.idx == 1 and op.sequence_id != 1:
					frappe.throw(
						_("Row #1: Sequence ID must be 1 for Operation {0}.").format(
							frappe.bold(op.operation)
						)
					)
				elif op.sequence_id != sequence_id and op.sequence_id != sequence_id + 1:
					frappe.throw(
						_("Row #{0}: Sequence ID must be {1} or {2} for Operation {3}.").format(
							op.idx,
							frappe.bold(sequence_id),
							frappe.bold(sequence_id + 1),
							frappe.bold(op.operation),
						)
					)
				sequence_id = op.sequence_id

	def validate_subcontracting_inward_order(self):
		if scio := self.subcontracting_inward_order:
			if self.source_warehouse != (
				rm_receipt_warehouse := frappe.get_cached_value(
					"Subcontracting Inward Order",
					scio,
					"customer_warehouse",
				)
			):
				frappe.throw(
					_(
						"Source Warehouse {0} must be same as Customer Warehouse {1} in the Subcontracting Inward Order."
					).format(
						get_link_to_form("Warehouse", self.source_warehouse),
						get_link_to_form("Warehouse", rm_receipt_warehouse),
					)
				)

			if self.fg_warehouse != (
				delivery_warehouse := frappe.get_cached_value(
					"Subcontracting Inward Order Item",
					self.subcontracting_inward_order_item,
					"delivery_warehouse",
				)
			):
				frappe.throw(
					_(
						"Target Warehouse {0} must be same as Delivery Warehouse {1} in the Subcontracting Inward Order Item."
					).format(
						get_link_to_form("Warehouse", self.fg_warehouse),
						get_link_to_form(
							"Warehouse",
							delivery_warehouse,
						),
					)
				)

			possible_customer_provided_items = frappe.get_all(
				"Subcontracting Inward Order Received Item",
				{
					"reference_name": self.subcontracting_inward_order_item,
					"is_customer_provided_item": 1,
					"docstatus": 1,
				},
				["rm_item_code", "received_qty", "returned_qty", "work_order_qty"],
			)
			item_codes = []
			for item in self.required_items:
				if item.is_customer_provided_item:
					if item.source_warehouse != self.source_warehouse:
						frappe.throw(
							_(
								"Row #{0}: Source Warehouse {1} for item {2} must be same as Source Warehouse {3} in the Work Order."
							).format(
								item.idx,
								get_link_to_form("Warehouse", item.source_warehouse),
								get_link_to_form("Item", item.item_code),
								get_link_to_form("Warehouse", self.source_warehouse),
							)
						)
					elif item.item_code in item_codes:
						frappe.throw(
							_("Row #{0}: Customer Provided Item {1} cannot be added multiple times.").format(
								item.idx,
								get_link_to_form("Item", item.item_code),
							)
						)
					else:
						row = next(
							(i for i in possible_customer_provided_items if i.rm_item_code == item.item_code),
							None,
						)
						if row:
							if item.required_qty > row.received_qty - row.returned_qty - row.work_order_qty:
								frappe.throw(
									_(
										"Row #{0}: Customer Provided Item {1} has insufficient quantity in the Subcontracting Inward Order. Available quantity is {2}."
									).format(
										item.idx,
										get_link_to_form("Item", item.item_code),
										frappe.bold(row.received_qty - row.returned_qty - row.work_order_qty),
									)
								)
							else:
								item_codes.append(item.item_code)
						else:
							frappe.throw(
								_(
									"Row #{0}: Customer Provided Item {1} does not exist in the Required Items table linked to the Subcontracting Inward Order."
								).format(
									item.idx,
									get_link_to_form("Item", item.item_code),
								)
							)
				elif frappe.get_cached_value("Warehouse", item.source_warehouse, "customer"):
					frappe.throw(
						_(
							"Row #{0}: Source Warehouse {1} for item {2} cannot be a customer warehouse."
						).format(
							item.idx,
							get_link_to_form("Warehouse", item.source_warehouse),
							get_link_to_form("Item", item.item_code),
						)
					)

	def set_warehouses(self):
		for row in self.required_items:
			if not row.source_warehouse:
				row.source_warehouse = self.source_warehouse

	def reset_use_multi_level_bom(self):
		if self.is_new():
			return

		before_save_obj = self.get_doc_before_save()
		if before_save_obj.use_multi_level_bom != self.use_multi_level_bom:
			self.get_items_and_operations_from_bom()

	def validate_workstation_type(self):
		if not self.docstatus.is_submitted():
			return

		for row in self.operations:
			if not row.workstation and not row.workstation_type:
				frappe.throw(
					_("Row {0}: Workstation or Workstation Type is mandatory for an operation {1}").format(
						row.idx, row.operation
					)
				)

	def validate_sales_order(self):
		if self.production_plan_sub_assembly_item:
			return

		production_item = self.production_item

		if self.material_request_item and (
			mr_plan_item := frappe.get_value(
				"Material Request Item", self.material_request_item, "material_request_plan_item"
			)
		):
			if main_item_code := frappe.get_value(
				"Material Request Plan Item", mr_plan_item, "main_item_code"
			):
				production_item = main_item_code

		if self.sales_order:
			check_on_hold_or_closed_status("Sales Order", self.sales_order)

			SalesOrder = frappe.qb.DocType("Sales Order")
			SalesOrderItem = frappe.qb.DocType("Sales Order Item")
			PackedItem = frappe.qb.DocType("Packed Item")
			ProductBundleItem = frappe.qb.DocType("Product Bundle Item")

			so = (
				frappe.qb.from_(SalesOrder)
				.inner_join(SalesOrderItem)
				.on(SalesOrderItem.parent == SalesOrder.name)
				.left_join(ProductBundleItem)
				.on(ProductBundleItem.parent == SalesOrderItem.item_code)
				.select(SalesOrder.name, SalesOrder.project, SalesOrderItem.delivery_date)
				.where(
					(SalesOrder.skip_delivery_note == 0)
					& (SalesOrder.docstatus == 1)
					& (SalesOrder.name == self.sales_order)
					& (
						(SalesOrderItem.item_code == production_item)
						| (ProductBundleItem.item_code == production_item)
					)
				)
				.run(as_dict=1)
			)

			if not so:
				so = (
					frappe.qb.from_(SalesOrder)
					.inner_join(SalesOrderItem)
					.on(SalesOrderItem.parent == SalesOrder.name)
					.inner_join(PackedItem)
					.on(PackedItem.parent == SalesOrder.name)
					.select(SalesOrder.name, SalesOrder.project, SalesOrderItem.delivery_date)
					.where(
						(SalesOrder.name == self.sales_order)
						& (SalesOrder.skip_delivery_note == 0)
						& (SalesOrderItem.item_code == PackedItem.parent_item)
						& (SalesOrder.docstatus == 1)
						& (PackedItem.item_code == production_item)
					)
					.run(as_dict=1)
				)

			if len(so):
				if not self.expected_delivery_date:
					self.expected_delivery_date = so[0].delivery_date

				if so[0].project:
					self.project = so[0].project

				if not self.material_request:
					self.validate_work_order_against_so()
			else:
				frappe.throw(_("Sales Order {0} is not valid").format(self.sales_order))

	def set_default_warehouse(self):
		if not self.wip_warehouse and not self.skip_transfer:
			self.wip_warehouse = frappe.get_cached_value("Company", self.company, "default_wip_warehouse")
		if not self.fg_warehouse:
			self.fg_warehouse = frappe.get_cached_value("Company", self.company, "default_fg_warehouse")

	def check_wip_warehouse_skip(self):
		if self.skip_transfer and not self.from_wip_warehouse:
			self.wip_warehouse = None

	def validate_warehouse_belongs_to_company(self):
		warehouses = [self.fg_warehouse, self.wip_warehouse]
		for d in self.get("required_items"):
			if d.source_warehouse not in warehouses:
				warehouses.append(d.source_warehouse)

		for wh in warehouses:
			validate_warehouse_company(wh, self.company)

	def validate_additional_transferred_qty(self):
		transfer_extra_materials_percentage = frappe.db.get_single_value(
			"Manufacturing Settings", "transfer_extra_materials_percentage"
		)

		allowed_qty = flt(self.qty) + flt(flt(self.qty) * flt(transfer_extra_materials_percentage) / 100)

		actual_qty = flt(self.material_transferred_for_manufacturing) + flt(self.additional_transferred_qty)

		precision = frappe.get_precision("Work Order", "qty")
		if flt(allowed_qty - actual_qty, precision) < 0:
			frappe.throw(
				_(
					"""Additional Transferred Qty {0}
					cannot be greater than {1}.
					To fix this, increase the percentage value
					of the field 'Transfer Extra Raw Materials to WIP'
					in Manufacturing Settings."""
				).format(actual_qty, allowed_qty),
			)

	def validate_warehouse(self):
		if self.track_semi_finished_goods:
			return

		if not self.wip_warehouse and not self.skip_transfer:
			frappe.throw(_("Work-in-Progress Warehouse is required before Submit"))
		if not self.fg_warehouse:
			frappe.throw(_("Target Warehouse is required before Submit"))

	def before_submit(self):
		self.create_serial_no_batch_no()

	def on_submit(self):
		self.validate_warehouse()
		if self.production_plan and frappe.db.exists(
			"Production Plan Item Reference", {"parent": self.production_plan}
		):
			self.update_work_order_qty_in_combined_so()
		else:
			self.update_work_order_qty_in_so()

		self.update_ordered_qty()
		self.update_reserved_qty_for_production()
		self.update_completed_qty_in_material_request()
		self.update_planned_qty()
		self.create_job_card_from_wo()

		if self.reserve_stock:
			StockReservationService(self).update_stock_reservation()

		self.update_subcontracting_inward_order_received_items()

	def on_cancel(self):
		self.validate_cancel()
		self.db_set("status", "Cancelled")

		self.on_close_or_cancel()

	def on_close_or_cancel(self):
		if self.production_plan and frappe.db.exists(
			"Production Plan Item Reference", {"parent": self.production_plan}
		):
			self.update_work_order_qty_in_combined_so()
		else:
			self.update_work_order_qty_in_so()

		self.update_completed_qty_in_material_request()
		self.update_planned_qty()
		self.update_ordered_qty()
		self.update_reserved_qty_for_production()

		if self.reserve_stock:
			StockReservationService(self).update_stock_reservation()

		self.update_subcontracting_inward_order_received_items()

	def set_qty_change(self):
		if scio_item_name := self.get("subcontracting_inward_order_item"):
			self.qty_change = frappe._dict()

			data = frappe.get_all(
				"Subcontracting Inward Order Received Item",
				{"reference_name": scio_item_name, "docstatus": 1, "is_customer_provided_item": 1},
				["rm_item_code", "required_qty as bom_qty", "work_order_qty", "received_qty"],
			)
			for d in data:
				wo_item = next(
					(
						wo_item
						for wo_item in self.get("required_items")
						if wo_item.item_code == d.rm_item_code
					),
					None,
				)

				if (
					wo_item
					and (d.work_order_qty + (wo_item.required_qty if self._action == "submit" else 0))
					== d.bom_qty
					and d.received_qty > d.bom_qty
				):
					self.qty_change[wo_item.name] = d.received_qty - d.bom_qty

	def update_subcontracting_inward_order_received_items(self):
		if scio_item_name := self.get("subcontracting_inward_order_item"):
			scio_rm_data = frappe.get_all(
				"Subcontracting Inward Order Received Item",
				filters={
					"reference_name": scio_item_name,
					"docstatus": 1,
					"rm_item_code": ["in", [d.item_code for d in self.get("required_items")]],
				},
				fields=["name", "rm_item_code"],
			)

			required_qty = {
				wo_item.item_code: wo_item.required_qty
				for wo_item in self.get("required_items")
				if wo_item.item_code in [d.rm_item_code for d in scio_rm_data]
			}

			table = frappe.qb.DocType("Subcontracting Inward Order Received Item")
			case_expr = Case()
			for item in scio_rm_data:
				case_expr = case_expr.when(
					table.rm_item_code == item.rm_item_code,
					table.work_order_qty
					+ (
						required_qty[item.rm_item_code]
						if self._action == "submit"
						else -required_qty[item.rm_item_code]
					),
				)

			frappe.qb.update(table).set(table.work_order_qty, case_expr).where(
				(table.name.isin([d.name for d in scio_rm_data])) & (table.docstatus == 1)
			).run()

	def create_serial_no_batch_no(self):
		if self.track_semi_finished_goods:
			return

		if not (self.has_serial_no or self.has_batch_no):
			return

		if not cint(
			frappe.db.get_single_value("Manufacturing Settings", "make_serial_no_batch_from_work_order")
		):
			return

		if self.has_batch_no:
			self.create_batch_for_finished_good()

		args = {"item_code": self.production_item, "work_order": self.name}

		if self.has_serial_no:
			self.make_serial_nos(args)

	def create_batch_for_finished_good(self):
		total_qty = self.qty
		if not self.batch_size:
			self.batch_size = total_qty

		batch_auto_creation = frappe.get_cached_value("Item", self.production_item, "create_new_batch")
		if not batch_auto_creation:
			frappe.msgprint(
				_("Batch not created for item {} since it does not have a batch series.").format(
					frappe.bold(self.production_item)
				),
				alert=True,
				indicator="orange",
			)
			return

		while total_qty > 0:
			qty = self.batch_size
			if self.batch_size >= total_qty:
				qty = total_qty

			if total_qty > self.batch_size:
				total_qty -= self.batch_size
			else:
				qty = total_qty
				total_qty = 0

			make_batch(
				frappe._dict(
					{
						"item": self.production_item,
						"qty_to_produce": qty,
						"reference_doctype": self.doctype,
						"reference_name": self.name,
					}
				)
			)

	def make_serial_nos(self, args):
		item_details = frappe.get_cached_value(
			"Item", self.production_item, ["serial_no_series", "item_name", "description"], as_dict=1
		)

		batches = []
		if self.has_batch_no:
			batches = frappe.get_all(
				"Batch", filters={"reference_name": self.name}, order_by="creation", pluck="name"
			)

		serial_nos = []
		if item_details.serial_no_series:
			serial_nos = get_available_serial_nos(item_details.serial_no_series, self.qty)

		if not serial_nos:
			return

		fields = [
			"name",
			"serial_no",
			"creation",
			"modified",
			"owner",
			"modified_by",
			"company",
			"item_code",
			"item_name",
			"description",
			"status",
			"work_order",
			"batch_no",
		]

		serial_nos_details = []
		index = 0
		for serial_no in serial_nos:
			index += 1
			batch_no = None
			if batches and self.batch_size:
				batch_no = batches[0]

				if index % self.batch_size == 0:
					batches.remove(batch_no)

			serial_nos_details.append(
				(
					serial_no,
					serial_no,
					now(),
					now(),
					frappe.session.user,
					frappe.session.user,
					self.company,
					self.production_item,
					item_details.item_name,
					item_details.description,
					"Inactive",
					self.name,
					batch_no,
				)
			)

		frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

	def validate_cancel(self):
		if self.status == "Stopped":
			frappe.throw(_("Stopped Work Order cannot be cancelled, Unstop it first to cancel"))

		# Check whether any stock entry exists against this Work Order
		stock_entry = frappe.db.sql(
			"""select name from `tabStock Entry`
			where work_order = %s and docstatus = 1""",
			self.name,
		)
		if stock_entry:
			frappe.throw(
				_("Cannot cancel because submitted Stock Entry {0} exists").format(
					frappe.utils.get_link_to_form("Stock Entry", stock_entry[0][0])
				)
			)

	def validate_production_item(self):
		if frappe.get_cached_value("Item", self.production_item, "has_variants"):
			frappe.throw(_("Work Order cannot be raised against a Item Template"), ItemHasVariantError)

		if self.production_item:
			validate_end_of_life(self.production_item)

	def validate_qty(self):
		if self.qty <= 0:
			frappe.throw(_("Quantity to Manufacture must be greater than 0."))

		if (
			self.stock_uom
			and frappe.get_cached_value("UOM", self.stock_uom, "must_be_whole_number")
			and abs(cint(self.qty) - flt(self.qty, self.precision("qty"))) > 0.0000001
		):
			frappe.throw(
				_(
					"Qty To Manufacture ({0}) cannot be a fraction for the UOM {2}. To allow this, disable '{1}' in the UOM {2}."
				).format(
					flt(self.qty, self.precision("qty")),
					frappe.bold(_("Must be Whole Number")),
					frappe.bold(self.stock_uom),
				),
			)

		if self.production_plan and self.production_plan_item and not self.production_plan_sub_assembly_item:
			qty_dict = frappe.db.get_value(
				"Production Plan Item", self.production_plan_item, ["planned_qty", "ordered_qty"], as_dict=1
			)

			if not qty_dict:
				return

			allowance_qty = (
				flt(
					frappe.db.get_single_value(
						"Manufacturing Settings", "overproduction_percentage_for_work_order"
					)
				)
				/ 100
				* qty_dict.get("planned_qty", 0)
			)

			max_qty = qty_dict.get("planned_qty", 0) + allowance_qty - qty_dict.get("ordered_qty", 0)

			if max_qty <= 0:
				frappe.throw(
					_("Cannot produce more item for {0}").format(self.production_item), OverProductionError
				)
			elif self.qty > max_qty:
				frappe.throw(
					_("Cannot produce more than {0} items for {1}").format(max_qty, self.production_item),
					OverProductionError,
				)

		if self.subcontracting_inward_order and self.qty > self.max_producible_qty:
			frappe.msgprint(
				_(
					"Warning: Quantity exceeds maximum producible quantity based on quantity of raw materials received through the Subcontracting Inward Order {0}."
				).format(get_link_to_form("Subcontracting Inward Order", self.subcontracting_inward_order)),
				alert=True,
				indicator="orange",
			)

	def validate_transfer_against(self):
		if self.docstatus != 1:
			# let user configure operations until they're ready to submit
			return
		if not self.operations:
			self.transfer_material_against = "Work Order"
		if not self.transfer_material_against:
			frappe.throw(
				_("Setting {0} is required").format(_(self.meta.get_label("transfer_material_against"))),
				title=_("Missing value"),
			)

	def validate_operations(self):
		for d in self.operations:
			if not d.batch_size or d.batch_size <= 0:
				d.batch_size = 1

			if d.time_in_mins <= 0:
				frappe.throw(_("Operation Time must be greater than 0 for Operation {0}").format(d.operation))

	@frappe.whitelist()
	def make_bom(self):
		data = frappe.db.sql(
			""" select sed.item_code, sed.qty, sed.s_warehouse
			from `tabStock Entry Detail` sed, `tabStock Entry` se
			where se.name = sed.parent and se.purpose = 'Manufacture'
			and (sed.t_warehouse is null or sed.t_warehouse = '') and se.docstatus = 1
			and se.work_order = %s""",
			(self.name),
			as_dict=1,
		)

		bom = frappe.new_doc("BOM")
		bom.item = self.production_item
		bom.conversion_rate = 1

		for d in data:
			bom.append("items", {"item_code": d.item_code, "qty": d.qty, "source_warehouse": d.s_warehouse})

		if self.operations:
			bom.set("operations", self.operations)
			bom.with_operations = 1

		bom.set_bom_material_details()
		return bom

	def calculate_operating_cost(self):
		return OperationsService(self).calculate_operating_cost()

	def set_work_order_operations(self):
		return OperationsService(self).set_work_order_operations()

	def update_operation_status(self):
		return OperationsService(self).update_operation_status()

	def set_actual_dates(self):
		return OperationsService(self).set_actual_dates()

	def create_job_card_from_wo(self):
		return OperationsService(self).create_job_card()

	def update_required_items(self):
		return RequiredItemsService(self).update_required_items()

	def update_reserved_qty_for_production(self, items=None):
		return RequiredItemsService(self).update_reserved_qty_for_production(items)

	@frappe.whitelist()
	def get_items_and_operations_from_bom(self):
		return RequiredItemsService(self).get_items_and_operations_from_bom()

	def set_available_qty(self):
		return RequiredItemsService(self).set_available_qty()

	def set_required_items(self, reset_only_qty=False, reset_source_warehouse=False):
		return RequiredItemsService(self).set_required_items(reset_only_qty, reset_source_warehouse)

	def update_transferred_qty_for_required_items(self):
		return RequiredItemsService(self).update_transferred_qty_for_required_items()

	def update_returned_qty(self):
		return RequiredItemsService(self).update_returned_qty()

	def update_consumed_qty_for_required_items(self):
		return RequiredItemsService(self).update_consumed_qty_for_required_items()

	def remove_additional_items(self, stock_entry):
		return RequiredItemsService(self).remove_additional_items(stock_entry)

	def add_additional_items(self, stock_entry):
		return RequiredItemsService(self).add_additional_items(stock_entry)

	def validate_work_order_against_so(self):
		return StatusService(self).validate_work_order_against_so()

	def update_status(self, status=None):
		return StatusService(self).update_status(status)

	def get_status(self, status=None):
		return StatusService(self).get_status(status)

	def update_work_order_qty(self):
		return StatusService(self).update_work_order_qty()

	def update_disassembled_qty(self, qty, is_cancel=False):
		return StatusService(self).update_disassembled_qty(qty, is_cancel)

	def get_transferred_or_manufactured_qty(self, purpose, fieldname):
		return StatusService(self).get_transferred_or_manufactured_qty(purpose, fieldname)

	def set_process_loss_qty(self):
		return StatusService(self).set_process_loss_qty()

	def update_production_plan_status(self):
		return StatusService(self).update_production_plan_status()

	def update_planned_qty(self):
		return StatusService(self).update_planned_qty()

	def set_produced_qty_for_sub_assembly_item(self):
		return StatusService(self).set_produced_qty_for_sub_assembly_item()

	def update_ordered_qty(self):
		return StatusService(self).update_ordered_qty()

	def update_work_order_qty_in_so(self):
		return StatusService(self).update_work_order_qty_in_so()

	def update_work_order_qty_in_combined_so(self):
		return StatusService(self).update_work_order_qty_in_combined_so()

	def update_completed_qty_in_material_request(self):
		return StatusService(self).update_completed_qty_in_material_request()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_bom_operations(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	if txt:
		filters["operation"] = ("like", "%%%s%%" % txt)

	return frappe.get_all("BOM Operation", filters=filters, fields=["operation"], as_list=1)


@frappe.whitelist()
def set_work_order_ops(name: str):
	po = frappe.get_doc("Work Order", name)
	po.set_work_order_operations()
	po.save()


@frappe.whitelist()
def get_disassembly_available_qty(stock_entry_name: str, current_se_name: str | None = None) -> float:
	se = frappe.db.get_value("Stock Entry", stock_entry_name, ["fg_completed_qty"], as_dict=True)
	if not se:
		return 0.0

	filters = {
		"source_stock_entry": stock_entry_name,
		"purpose": "Disassemble",
		"docstatus": 1,
	}

	if current_se_name:
		filters["name"] = ("!=", current_se_name)

	already_disassembled = flt(frappe.db.get_value("Stock Entry", filters, [{"SUM": "fg_completed_qty"}]))

	return flt(se.fg_completed_qty) - already_disassembled


@frappe.whitelist()
def get_default_warehouse(company: str):
	wip, fg, scrap = frappe.get_cached_value(
		"Company", company, ["default_wip_warehouse", "default_fg_warehouse", "default_scrap_warehouse"]
	)
	return {
		"wip_warehouse": wip,
		"fg_warehouse": fg,
		"scrap_warehouse": scrap,
	}


@frappe.whitelist()
def stop_unstop(work_order: str, status: str):
	"""Called from client side on Stop/Unstop event"""

	if not frappe.has_permission("Work Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	pro_order = frappe.get_doc("Work Order", work_order)

	if pro_order.status == "Closed":
		frappe.throw(_("Closed Work Order can not be stopped or Re-opened"))

	pro_order.update_status(status)
	pro_order.update_planned_qty()
	frappe.msgprint(_("Work Order has been {0}").format(status))
	pro_order.notify_update()

	return pro_order.status


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def query_sales_order(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	return frappe.get_list(
		"Sales Order",
		fields=["name"],
		filters=[
			["Sales Order", "docstatus", "=", 1],
		],
		or_filters=[
			["Sales Order Item", "item_code", "=", filters.get("production_item")],
			["Packed Item", "item_code", "=", filters.get("production_item")],
		],
		as_list=True,
		distinct=True,
	)


@frappe.whitelist()
def close_work_order(work_order: str, status: str):
	if not frappe.has_permission("Work Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	work_order = frappe.get_doc("Work Order", work_order)
	if work_order.get("operations"):
		job_cards = frappe.get_list(
			"Job Card",
			filters={"work_order": work_order.name, "status": "Work In Progress", "docstatus": 1},
			pluck="name",
		)

		if job_cards:
			job_cards = ", ".join(job_cards)
			frappe.throw(
				_("Can not close Work Order. Since {0} Job Cards are in Work In Progress state.").format(
					job_cards
				)
			)

	work_order.update_status(status)
	work_order.on_close_or_cancel()
	frappe.msgprint(_("Work Order has been {0}").format(status))
	work_order.notify_update()
	return work_order.status

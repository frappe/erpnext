# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from frappe.utils import (
	cint,
	date_diff,
	flt,
	get_datetime,
	get_link_to_form,
	getdate,
	now,
	nowdate,
	time_diff_in_hours,
)
from pypika import functions as fn

from erpnext.manufacturing.doctype.bom.bom import (
	get_bom_item_rate,
	get_bom_items_as_dict,
	validate_bom_no,
)
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_mins_between_operations,
)
from erpnext.stock.doctype.batch.batch import make_batch
from erpnext.stock.doctype.item.item import get_item_defaults, validate_end_of_life
from erpnext.stock.doctype.serial_no.serial_no import get_available_serial_nos, get_serial_nos
from erpnext.stock.stock_balance import get_planned_qty, update_bin_qty
from erpnext.stock.utils import get_bin, get_latest_stock_qty, validate_warehouse_company
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

		from erpnext.manufacturing.doctype.work_order_item.work_order_item import WorkOrderItem
		from erpnext.manufacturing.doctype.work_order_operation.work_order_operation import (
			WorkOrderOperation,
		)

		actual_end_date: DF.Datetime | None
		actual_operating_cost: DF.Currency
		actual_start_date: DF.Datetime | None
		additional_operating_cost: DF.Currency
		allow_alternative_item: DF.Check
		amended_from: DF.Link | None
		batch_size: DF.Float
		bom_no: DF.Link
		company: DF.Link
		corrective_operation_cost: DF.Currency
		description: DF.SmallText | None
		expected_delivery_date: DF.Date | None
		fg_warehouse: DF.Link
		from_wip_warehouse: DF.Check
		has_batch_no: DF.Check
		has_serial_no: DF.Check
		image: DF.AttachImage | None
		item_name: DF.Data | None
		lead_time: DF.Float
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		material_transferred_for_manufacturing: DF.Float
		naming_series: DF.Literal["MFG-WO-.YYYY.-"]
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
		sales_order: DF.Link | None
		sales_order_item: DF.Data | None
		scrap_warehouse: DF.Link | None
		skip_transfer: DF.Check
		source_warehouse: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"Submitted",
			"Not Started",
			"In Process",
			"Completed",
			"Stopped",
			"Closed",
			"Cancelled",
		]
		stock_uom: DF.Link | None
		total_operating_cost: DF.Currency
		transfer_material_against: DF.Literal["", "Work Order", "Job Card"]
		update_consumed_material_cost_in_project: DF.Check
		use_multi_level_bom: DF.Check
		wip_warehouse: DF.Link | None
	# end: auto-generated types

	def onload(self):
		ms = frappe.get_doc("Manufacturing Settings")
		self.set_onload("material_consumption", ms.material_consumption)
		self.set_onload("backflush_raw_materials_based_on", ms.backflush_raw_materials_based_on)
		self.set_onload("overproduction_percentage", ms.overproduction_percentage_for_work_order)

	def validate(self):
		self.validate_production_item()
		if self.bom_no:
			validate_bom_no(self.production_item, self.bom_no)

		self.validate_sales_order()
		self.set_default_warehouse()
		self.validate_warehouse_belongs_to_company()
		self.check_wip_warehouse_skip()
		self.calculate_operating_cost()
		self.validate_qty()
		self.validate_transfer_against()
		self.validate_operation_time()
		self.status = self.get_status()
		self.validate_workstation_type()
		self.reset_use_multi_level_bom()

		if self.source_warehouse:
			self.set_warehouses()

		validate_uom_is_integer(self, "stock_uom", ["qty", "produced_qty"])

		self.set_required_items(reset_only_qty=len(self.get("required_items")))

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
		if self.sales_order:
			self.check_sales_order_on_hold_or_close()
			so = frappe.db.sql(
				"""
				select so.name, so_item.delivery_date, so.project
				from `tabSales Order` so
				inner join `tabSales Order Item` so_item on so_item.parent = so.name
				left join `tabProduct Bundle Item` pk_item on so_item.item_code = pk_item.parent
				where so.name=%s and so.docstatus = 1
					and so.skip_delivery_note  = 0 and (
					so_item.item_code=%s or
					pk_item.item_code=%s )
			""",
				(self.sales_order, self.production_item, self.production_item),
				as_dict=1,
			)

			if not so:
				so = frappe.db.sql(
					"""
					select
						so.name, so_item.delivery_date, so.project
					from
						`tabSales Order` so, `tabSales Order Item` so_item, `tabPacked Item` packed_item
					where so.name=%s
						and so.name=so_item.parent
						and so.name=packed_item.parent
						and so.skip_delivery_note = 0
						and so_item.item_code = packed_item.parent_item
						and so.docstatus = 1 and packed_item.item_code=%s
				""",
					(self.sales_order, self.production_item),
					as_dict=1,
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

	def check_sales_order_on_hold_or_close(self):
		status = frappe.db.get_value("Sales Order", self.sales_order, "status")
		if status in ("Closed", "On Hold"):
			frappe.throw(_("Sales Order {0} is {1}").format(self.sales_order, status))

	def set_default_warehouse(self):
		if not self.wip_warehouse and not self.skip_transfer:
			self.wip_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_wip_warehouse")
		if not self.fg_warehouse:
			self.fg_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_fg_warehouse")

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

	def calculate_operating_cost(self):
		self.planned_operating_cost, self.actual_operating_cost = 0.0, 0.0
		for d in self.get("operations"):
			d.planned_operating_cost = flt(
				flt(d.hour_rate) * (flt(d.time_in_mins) / 60.0), d.precision("planned_operating_cost")
			)
			d.actual_operating_cost = flt(
				flt(d.hour_rate) * (flt(d.actual_operation_time) / 60.0), d.precision("actual_operating_cost")
			)

			self.planned_operating_cost += flt(d.planned_operating_cost)
			self.actual_operating_cost += flt(d.actual_operating_cost)

		variable_cost = (
			self.actual_operating_cost if self.actual_operating_cost else self.planned_operating_cost
		)

		self.total_operating_cost = (
			flt(self.additional_operating_cost) + flt(variable_cost) + flt(self.corrective_operation_cost)
		)

	def validate_work_order_against_so(self):
		# already ordered qty
		ordered_qty_against_so = frappe.db.sql(
			"""select sum(qty) from `tabWork Order`
			where production_item = %s and sales_order = %s and docstatus < 2 and name != %s""",
			(self.production_item, self.sales_order, self.name),
		)[0][0]

		total_qty = flt(ordered_qty_against_so) + flt(self.qty)

		# get qty from Sales Order Item table
		so_item_qty = frappe.db.sql(
			"""select sum(stock_qty) from `tabSales Order Item`
			where parent = %s and item_code = %s""",
			(self.sales_order, self.production_item),
		)[0][0]
		# get qty from Packing Item table
		dnpi_qty = frappe.db.sql(
			"""select sum(qty) from `tabPacked Item`
			where parent = %s and parenttype = 'Sales Order' and item_code = %s""",
			(self.sales_order, self.production_item),
		)[0][0]
		# total qty in SO
		so_qty = flt(so_item_qty) + flt(dnpi_qty)

		allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_sales_order")
		)

		if total_qty > so_qty + (allowance_percentage / 100 * so_qty):
			frappe.throw(
				_("Cannot produce more Item {0} than Sales Order quantity {1}").format(
					self.production_item, so_qty
				),
				OverProductionError,
			)

	def update_status(self, status=None):
		"""Update status of work order if unknown"""
		if status != "Stopped" and status != "Closed":
			status = self.get_status(status)

		if status != self.status:
			self.db_set("status", status)

		self.update_required_items()

		return status

	def get_status(self, status=None):
		"""Return the status based on stock entries against this work order"""
		if not status:
			status = self.status

		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			if status != "Stopped":
				status = "Not Started"
				if flt(self.material_transferred_for_manufacturing) > 0:
					status = "In Process"

				total_qty = flt(self.produced_qty) + flt(self.process_loss_qty)
				if flt(total_qty) >= flt(self.qty):
					status = "Completed"
		else:
			status = "Cancelled"

		if (
			self.skip_transfer
			and self.produced_qty
			and self.qty > (flt(self.produced_qty) + flt(self.process_loss_qty))
		):
			status = "In Process"

		return status

	def update_work_order_qty(self):
		"""Update **Manufactured Qty** and **Material Transferred for Qty** in Work Order
		based on Stock Entry"""

		allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)

		for purpose, fieldname in (
			("Manufacture", "produced_qty"),
			("Material Transfer for Manufacture", "material_transferred_for_manufacturing"),
		):
			if (
				purpose == "Material Transfer for Manufacture"
				and self.operations
				and self.transfer_material_against == "Job Card"
			):
				continue

			qty = self.get_transferred_or_manufactured_qty(purpose)

			completed_qty = self.qty + (allowance_percentage / 100 * self.qty)
			if qty > completed_qty:
				frappe.throw(
					_("{0} ({1}) cannot be greater than planned quantity ({2}) in Work Order {3}").format(
						self.meta.get_label(fieldname), qty, completed_qty, self.name
					),
					StockOverProductionError,
				)

			self.db_set(fieldname, qty)
			self.set_process_loss_qty()

			from erpnext.selling.doctype.sales_order.sales_order import update_produced_qty_in_so_item

			if self.sales_order and self.sales_order_item:
				update_produced_qty_in_so_item(self.sales_order, self.sales_order_item)

		if self.production_plan:
			self.set_produced_qty_for_sub_assembly_item()
			self.update_production_plan_status()

	def get_transferred_or_manufactured_qty(self, purpose):
		table = frappe.qb.DocType("Stock Entry")
		query = frappe.qb.from_(table).where(
			(table.work_order == self.name) & (table.docstatus == 1) & (table.purpose == purpose)
		)

		if purpose == "Manufacture":
			query = query.select(Sum(table.fg_completed_qty) - Sum(table.process_loss_qty))
		else:
			query = query.select(Sum(table.fg_completed_qty))

		return flt(query.run()[0][0])

	def set_process_loss_qty(self):
		table = frappe.qb.DocType("Stock Entry")
		process_loss_qty = (
			frappe.qb.from_(table)
			.select(Sum(table.process_loss_qty))
			.where(
				(table.work_order == self.name) & (table.purpose == "Manufacture") & (table.docstatus == 1)
			)
		).run()[0][0]

		self.db_set("process_loss_qty", flt(process_loss_qty))

	def update_production_plan_status(self):
		production_plan = frappe.get_doc("Production Plan", self.production_plan)
		produced_qty = 0
		if self.production_plan_item:
			total_qty = frappe.get_all(
				"Work Order",
				fields="sum(produced_qty) as produced_qty",
				filters={
					"docstatus": 1,
					"production_plan": self.production_plan,
					"production_plan_item": self.production_plan_item,
				},
				as_list=1,
			)

			produced_qty = total_qty[0][0] if total_qty else 0

		self.update_status()
		production_plan.run_method("update_produced_pending_qty", produced_qty, self.production_plan_item)

	def before_submit(self):
		self.create_serial_no_batch_no()

	def on_submit(self):
		if not self.wip_warehouse and not self.skip_transfer:
			frappe.throw(_("Work-in-Progress Warehouse is required before Submit"))
		if not self.fg_warehouse:
			frappe.throw(_("For Warehouse is required before Submit"))

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
		self.create_job_card()

	def on_cancel(self):
		self.validate_cancel()
		self.db_set("status", "Cancelled")

		if self.production_plan and frappe.db.exists(
			"Production Plan Item Reference", {"parent": self.production_plan}
		):
			self.update_work_order_qty_in_combined_so()
		else:
			self.update_work_order_qty_in_so()

		self.delete_job_card()
		self.update_completed_qty_in_material_request()
		self.update_planned_qty()
		self.update_ordered_qty()
		self.update_reserved_qty_for_production()
		self.delete_auto_created_batch_and_serial_no()

	def create_serial_no_batch_no(self):
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

	def delete_auto_created_batch_and_serial_no(self):
		for row in frappe.get_all("Serial No", filters={"work_order": self.name}):
			frappe.delete_doc("Serial No", row.name)

		for row in frappe.get_all("Batch", filters={"reference_name": self.name}):
			frappe.delete_doc("Batch", row.name)

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

	def create_job_card(self):
		manufacturing_settings_doc = frappe.get_doc("Manufacturing Settings")

		enable_capacity_planning = not cint(manufacturing_settings_doc.disable_capacity_planning)
		plan_days = cint(manufacturing_settings_doc.capacity_planning_for_days) or 30

		for index, row in enumerate(self.operations):
			qty = self.qty
			while qty > 0:
				qty = split_qty_based_on_batch_size(self, row, qty)
				if row.job_card_qty > 0:
					self.prepare_data_for_job_card(row, index, plan_days, enable_capacity_planning)

		planned_end_date = self.operations and self.operations[-1].planned_end_time
		if planned_end_date:
			self.db_set("planned_end_date", planned_end_date)

	def prepare_data_for_job_card(self, row, index, plan_days, enable_capacity_planning):
		self.set_operation_start_end_time(index, row)

		job_card_doc = create_job_card(
			self, row, auto_create=True, enable_capacity_planning=enable_capacity_planning
		)

		if enable_capacity_planning and job_card_doc:
			row.planned_start_time = job_card_doc.scheduled_time_logs[-1].from_time
			row.planned_end_time = job_card_doc.scheduled_time_logs[-1].to_time

			if date_diff(row.planned_end_time, self.planned_start_date) > plan_days:
				frappe.message_log.pop()
				frappe.throw(
					_(
						"Unable to find the time slot in the next {0} days for the operation {1}. Please increase the 'Capacity Planning For (Days)' in the {2}."
					).format(
						plan_days,
						row.operation,
						get_link_to_form("Manufacturing Settings", "Manufacturing Settings"),
					),
					CapacityError,
				)

			row.db_update()

	def set_operation_start_end_time(self, idx, row):
		"""Set start and end time for given operation. If first operation, set start as
		`planned_start_date`, else add time diff to end time of earlier operation."""
		if idx == 0:
			# first operation at planned_start date
			row.planned_start_time = self.planned_start_date
		else:
			row.planned_start_time = (
				get_datetime(self.operations[idx - 1].planned_end_time) + get_mins_between_operations()
			)

		row.planned_end_time = get_datetime(row.planned_start_time) + relativedelta(minutes=row.time_in_mins)

		if row.planned_start_time == row.planned_end_time:
			frappe.throw(_("Capacity Planning Error, planned start time can not be same as end time"))

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

	def update_planned_qty(self):
		from erpnext.manufacturing.doctype.production_plan.production_plan import (
			get_reserved_qty_for_sub_assembly,
		)

		qty_dict = {"planned_qty": get_planned_qty(self.production_item, self.fg_warehouse)}

		if self.production_plan_sub_assembly_item and self.production_plan:
			qty_dict["reserved_qty_for_production_plan"] = get_reserved_qty_for_sub_assembly(
				self.production_item, self.fg_warehouse
			)

		update_bin_qty(
			self.production_item,
			self.fg_warehouse,
			qty_dict,
		)

		if self.material_request:
			mr_obj = frappe.get_doc("Material Request", self.material_request)
			mr_obj.update_requested_qty([self.material_request_item])

	def set_produced_qty_for_sub_assembly_item(self):
		table = frappe.qb.DocType("Work Order")

		query = (
			frappe.qb.from_(table)
			.select(Sum(table.produced_qty))
			.where(
				(table.production_plan == self.production_plan)
				& (table.production_plan_sub_assembly_item == self.production_plan_sub_assembly_item)
				& (table.docstatus == 1)
			)
		).run()

		produced_qty = flt(query[0][0]) if query else 0

		frappe.db.set_value(
			"Production Plan Sub Assembly Item",
			self.production_plan_sub_assembly_item,
			"wo_produced_qty",
			produced_qty,
		)

	def update_ordered_qty(self):
		if self.production_plan and self.production_plan_item and not self.production_plan_sub_assembly_item:
			table = frappe.qb.DocType("Work Order")

			query = (
				frappe.qb.from_(table)
				.select(Sum(table.qty))
				.where(
					(table.production_plan == self.production_plan)
					& (table.production_plan_item == self.production_plan_item)
					& (table.docstatus == 1)
				)
			).run()

			qty = flt(query[0][0]) if query else 0

			frappe.db.set_value("Production Plan Item", self.production_plan_item, "ordered_qty", qty)

			doc = frappe.get_doc("Production Plan", self.production_plan)
			doc.set_status()
			doc.db_set("status", doc.status)

	def update_work_order_qty_in_so(self):
		if not self.sales_order and not self.sales_order_item:
			return

		total_bundle_qty = 1
		if self.product_bundle_item:
			total_bundle_qty = frappe.db.sql(
				""" select sum(qty) from
				`tabProduct Bundle Item` where parent = %s""",
				(frappe.db.escape(self.product_bundle_item)),
			)[0][0]

			if not total_bundle_qty:
				# product bundle is 0 (product bundle allows 0 qty for items)
				total_bundle_qty = 1

		cond = "product_bundle_item = %s" if self.product_bundle_item else "production_item = %s"

		qty = frappe.db.sql(
			f""" select sum(qty) from
			`tabWork Order` where sales_order = %s and docstatus = 1 and {cond}
			""",
			(self.sales_order, (self.product_bundle_item or self.production_item)),
			as_list=1,
		)

		work_order_qty = qty[0][0] if qty and qty[0][0] else 0
		frappe.db.set_value(
			"Sales Order Item",
			self.sales_order_item,
			"work_order_qty",
			flt(work_order_qty / total_bundle_qty, 2),
		)

	def update_work_order_qty_in_combined_so(self):
		total_bundle_qty = 1
		if self.product_bundle_item:
			total_bundle_qty = frappe.db.sql(
				""" select sum(qty) from
				`tabProduct Bundle Item` where parent = %s""",
				(frappe.db.escape(self.product_bundle_item)),
			)[0][0]

			if not total_bundle_qty:
				# product bundle is 0 (product bundle allows 0 qty for items)
				total_bundle_qty = 1

		prod_plan = frappe.get_doc("Production Plan", self.production_plan)
		item_reference = frappe.get_value(
			"Production Plan Item", self.production_plan_item, "sales_order_item"
		)

		for plan_reference in prod_plan.prod_plan_references:
			work_order_qty = 0.0
			if plan_reference.item_reference == item_reference:
				if self.docstatus == 1:
					work_order_qty = flt(plan_reference.qty) / total_bundle_qty
				frappe.db.set_value(
					"Sales Order Item", plan_reference.sales_order_item, "work_order_qty", work_order_qty
				)

	def update_completed_qty_in_material_request(self):
		if self.material_request and self.material_request_item:
			frappe.get_doc("Material Request", self.material_request).update_completed_qty(
				[self.material_request_item]
			)

	def set_work_order_operations(self):
		"""Fetch operations from BOM and set in 'Work Order'"""

		def _get_operations(bom_no, qty=1):
			data = frappe.get_all(
				"BOM Operation",
				filters={"parent": bom_no},
				fields=[
					"operation",
					"description",
					"workstation",
					"idx",
					"workstation_type",
					"base_hour_rate as hour_rate",
					"time_in_mins",
					"parent as bom",
					"batch_size",
					"sequence_id",
					"fixed_time",
				],
				order_by="idx",
			)

			for d in data:
				if not d.fixed_time:
					d.time_in_mins = flt(d.time_in_mins) * flt(qty)
				d.status = "Pending"

			return data

		self.set("operations", [])
		if not self.bom_no or not frappe.get_cached_value("BOM", self.bom_no, "with_operations"):
			return

		operations = []

		if self.use_multi_level_bom:
			bom_tree = frappe.get_doc("BOM", self.bom_no).get_tree_representation()
			bom_traversal = reversed(bom_tree.level_order_traversal())

			for node in bom_traversal:
				if node.is_bom:
					operations.extend(_get_operations(node.name, qty=node.exploded_qty / node.bom_qty))

		bom_qty = frappe.get_cached_value("BOM", self.bom_no, "quantity")
		operations.extend(_get_operations(self.bom_no, qty=1.0 / bom_qty))

		for correct_index, operation in enumerate(operations, start=1):
			operation.idx = correct_index

		self.set("operations", operations)
		self.calculate_time()

	def calculate_time(self):
		for d in self.get("operations"):
			if not d.fixed_time:
				d.time_in_mins = flt(d.time_in_mins) * (flt(self.qty) / flt(d.batch_size))

		self.calculate_operating_cost()

	def get_holidays(self, workstation):
		holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")

		holidays = {}

		if holiday_list not in holidays:
			holiday_list_days = [
				getdate(d[0])
				for d in frappe.get_all(
					"Holiday",
					fields=["holiday_date"],
					filters={"parent": holiday_list},
					order_by="holiday_date",
					limit_page_length=0,
					as_list=1,
				)
			]

			holidays[holiday_list] = holiday_list_days

		return holidays[holiday_list]

	def update_operation_status(self):
		allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)
		max_allowed_qty_for_wo = flt(self.qty) + (allowance_percentage / 100 * flt(self.qty))

		for d in self.get("operations"):
			precision = d.precision("completed_qty")
			qty = flt(d.completed_qty, precision) + flt(d.process_loss_qty, precision)
			if not qty:
				d.status = "Pending"
			elif flt(qty) < flt(self.qty):
				d.status = "Work in Progress"
			elif flt(qty) == flt(self.qty):
				d.status = "Completed"
			elif flt(qty) <= max_allowed_qty_for_wo:
				d.status = "Completed"
			else:
				frappe.throw(_("Completed Qty cannot be greater than 'Qty to Manufacture'"))

	def set_actual_dates(self):
		if self.get("operations"):
			actual_start_dates = [d.actual_start_time for d in self.get("operations") if d.actual_start_time]
			if actual_start_dates:
				self.actual_start_date = min(actual_start_dates)

			actual_end_dates = [d.actual_end_time for d in self.get("operations") if d.actual_end_time]
			if actual_end_dates:
				self.actual_end_date = max(actual_end_dates)
		else:
			data = frappe.get_all(
				"Stock Entry",
				fields=["timestamp(posting_date, posting_time) as posting_datetime"],
				filters={
					"work_order": self.name,
					"purpose": ("in", ["Material Transfer for Manufacture", "Manufacture"]),
				},
			)

			if data and len(data):
				dates = [d.posting_datetime for d in data]
				self.db_set("actual_start_date", min(dates))

				if self.status == "Completed":
					self.db_set("actual_end_date", max(dates))

		self.set_lead_time()

	def set_lead_time(self):
		if self.actual_start_date and self.actual_end_date:
			self.lead_time = flt(time_diff_in_hours(self.actual_end_date, self.actual_start_date) * 60)

	def delete_job_card(self):
		for d in frappe.get_all("Job Card", ["name"], {"work_order": self.name}):
			frappe.delete_doc("Job Card", d.name)

	def validate_production_item(self):
		if frappe.get_cached_value("Item", self.production_item, "has_variants"):
			frappe.throw(_("Work Order cannot be raised against a Item Template"), ItemHasVariantError)

		if self.production_item:
			validate_end_of_life(self.production_item)

	def validate_qty(self):
		if not self.qty > 0:
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

			if not max_qty > 0:
				frappe.throw(
					_("Cannot produce more item for {0}").format(self.production_item), OverProductionError
				)
			elif self.qty > max_qty:
				frappe.throw(
					_("Cannot produce more than {0} items for {1}").format(max_qty, self.production_item),
					OverProductionError,
				)

	def validate_transfer_against(self):
		if not self.docstatus == 1:
			# let user configure operations until they're ready to submit
			return
		if not self.operations:
			self.transfer_material_against = "Work Order"
		if not self.transfer_material_against:
			frappe.throw(
				_("Setting {} is required").format(self.meta.get_label("transfer_material_against")),
				title=_("Missing value"),
			)

	def validate_operation_time(self):
		for d in self.operations:
			if not d.time_in_mins > 0:
				frappe.throw(_("Operation Time must be greater than 0 for Operation {0}").format(d.operation))

	def update_required_items(self):
		"""
		update bin reserved_qty_for_production
		called from Stock Entry for production, after submit, cancel
		"""
		# calculate consumed qty based on submitted stock entries
		self.update_consumed_qty_for_required_items()

		if self.docstatus == 1:
			# calculate transferred qty based on submitted stock entries
			self.update_transferred_qty_for_required_items()
			self.update_returned_qty()

			# update in bin
			self.update_reserved_qty_for_production()

	def update_reserved_qty_for_production(self, items=None):
		"""update reserved_qty_for_production in bins"""
		for d in self.required_items:
			if d.source_warehouse:
				stock_bin = get_bin(d.item_code, d.source_warehouse)
				stock_bin.update_reserved_qty_for_production()

	@frappe.whitelist()
	def get_items_and_operations_from_bom(self):
		self.set_required_items()
		self.set_work_order_operations()

		return check_if_scrap_warehouse_mandatory(self.bom_no)

	def set_available_qty(self):
		for d in self.get("required_items"):
			if d.source_warehouse:
				d.available_qty_at_source_warehouse = get_latest_stock_qty(d.item_code, d.source_warehouse)

			if self.wip_warehouse:
				d.available_qty_at_wip_warehouse = get_latest_stock_qty(d.item_code, self.wip_warehouse)

	def set_required_items(self, reset_only_qty=False):
		"""set required_items for production to keep track of reserved qty"""
		if not reset_only_qty:
			self.required_items = []

		operation = None
		if self.get("operations") and len(self.operations) == 1:
			operation = self.operations[0].operation

		if self.bom_no and self.qty:
			item_dict = get_bom_items_as_dict(
				self.bom_no, self.company, qty=self.qty, fetch_exploded=self.use_multi_level_bom
			)

			if reset_only_qty:
				for d in self.get("required_items"):
					if item_dict.get(d.item_code):
						d.required_qty = item_dict.get(d.item_code).get("qty")

					if not d.operation:
						d.operation = operation
			else:
				for item in sorted(item_dict.values(), key=lambda d: d["idx"] or float("inf")):
					self.append(
						"required_items",
						{
							"rate": item.rate,
							"amount": item.rate * item.qty,
							"operation": item.operation or operation,
							"item_code": item.item_code,
							"item_name": item.item_name,
							"description": item.description,
							"allow_alternative_item": item.allow_alternative_item,
							"required_qty": item.qty,
							"source_warehouse": item.source_warehouse or item.default_warehouse,
							"include_item_in_manufacturing": item.include_item_in_manufacturing,
						},
					)

					if not self.project:
						self.project = item.get("project")

			self.set_available_qty()

	def update_transferred_qty_for_required_items(self):
		ste = frappe.qb.DocType("Stock Entry")
		ste_child = frappe.qb.DocType("Stock Entry Detail")

		query = (
			frappe.qb.from_(ste)
			.inner_join(ste_child)
			.on(ste_child.parent == ste.name)
			.select(
				ste_child.item_code,
				ste_child.original_item,
				fn.Sum(ste_child.qty).as_("qty"),
			)
			.where(
				(ste.docstatus == 1)
				& (ste.work_order == self.name)
				& (ste.purpose == "Material Transfer for Manufacture")
				& (ste.is_return == 0)
			)
			.groupby(ste_child.item_code)
		)

		data = query.run(as_dict=1) or []
		transferred_items = frappe._dict({d.original_item or d.item_code: d.qty for d in data})

		for row in self.required_items:
			row.db_set(
				"transferred_qty", (transferred_items.get(row.item_code) or 0.0), update_modified=False
			)

	def update_returned_qty(self):
		ste = frappe.qb.DocType("Stock Entry")
		ste_child = frappe.qb.DocType("Stock Entry Detail")

		query = (
			frappe.qb.from_(ste)
			.inner_join(ste_child)
			.on(ste_child.parent == ste.name)
			.select(
				ste_child.item_code,
				ste_child.original_item,
				fn.Sum(ste_child.qty).as_("qty"),
			)
			.where(
				(ste.docstatus == 1)
				& (ste.work_order == self.name)
				& (ste.purpose == "Material Transfer for Manufacture")
				& (ste.is_return == 1)
			)
			.groupby(ste_child.item_code)
		)

		data = query.run(as_dict=1) or []
		returned_dict = frappe._dict({d.original_item or d.item_code: d.qty for d in data})

		for row in self.required_items:
			row.db_set("returned_qty", (returned_dict.get(row.item_code) or 0.0), update_modified=False)

	def update_consumed_qty_for_required_items(self):
		"""
		Update consumed qty from submitted stock entries
		against a work order for each stock item
		"""

		for item in self.required_items:
			consumed_qty = frappe.db.sql(
				"""
				SELECT
					SUM(detail.qty)
				FROM
					`tabStock Entry` entry,
					`tabStock Entry Detail` detail
				WHERE
					entry.work_order = %(name)s
						AND (entry.purpose = "Material Consumption for Manufacture"
							OR entry.purpose = "Manufacture")
						AND entry.docstatus = 1
						AND detail.parent = entry.name
						AND detail.s_warehouse IS NOT null
						AND (detail.item_code = %(item)s
							OR detail.original_item = %(item)s)
				""",
				{"name": self.name, "item": item.item_code},
			)[0][0]

			item.db_set("consumed_qty", flt(consumed_qty), update_modified=False)

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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_bom_operations(doctype, txt, searchfield, start, page_len, filters):
	if txt:
		filters["operation"] = ("like", "%%%s%%" % txt)

	return frappe.get_all("BOM Operation", filters=filters, fields=["operation"], as_list=1)


@frappe.whitelist()
def get_item_details(item, project=None, skip_bom_info=False, throw=True):
	res = frappe.db.sql(
		"""
		select stock_uom, description, item_name, allow_alternative_item,
			include_item_in_manufacturing
		from `tabItem`
		where disabled=0
			and (end_of_life is null or end_of_life='0000-00-00' or end_of_life > %s)
			and name=%s
	""",
		(nowdate(), item),
		as_dict=1,
	)

	if not res:
		return {}

	res = res[0]
	if skip_bom_info:
		return res

	filters = {"item": item, "is_default": 1, "docstatus": 1}

	if project:
		filters = {"item": item, "project": project}

	res["bom_no"] = frappe.db.get_value("BOM", filters=filters)

	if not res["bom_no"]:
		variant_of = frappe.db.get_value("Item", item, "variant_of")

		if variant_of:
			res["bom_no"] = frappe.db.get_value("BOM", filters={"item": variant_of, "is_default": 1})

	if not res["bom_no"]:
		if project:
			res = get_item_details(item, throw=throw)
			frappe.msgprint(
				_("Default BOM not found for Item {0} and Project {1}").format(item, project), alert=1
			)
		else:
			msg = _("Default BOM for {0} not found").format(item)
			frappe.msgprint(msg, raise_exception=throw, indicator="yellow", alert=(not throw))

			return res

	bom_data = frappe.db.get_value(
		"BOM",
		res["bom_no"],
		["project", "allow_alternative_item", "transfer_material_against", "item_name"],
		as_dict=1,
	)

	res["project"] = project or bom_data.pop("project")
	res.update(bom_data)
	res.update(check_if_scrap_warehouse_mandatory(res["bom_no"]))

	return res


@frappe.whitelist()
def make_work_order(bom_no, item, qty=0, project=None, variant_items=None, use_multi_level_bom=None):
	if not frappe.has_permission("Work Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	item_details = get_item_details(item, project)

	wo_doc = frappe.new_doc("Work Order")
	wo_doc.production_item = item
	wo_doc.update(item_details)
	wo_doc.bom_no = bom_no
	wo_doc.use_multi_level_bom = cint(use_multi_level_bom)

	if flt(qty) > 0:
		wo_doc.qty = flt(qty)
		wo_doc.get_items_and_operations_from_bom()

	if variant_items and not wo_doc.use_multi_level_bom:
		add_variant_item(variant_items, wo_doc, bom_no, "required_items")

	return wo_doc


def add_variant_item(variant_items, wo_doc, bom_no, table_name="items"):
	if isinstance(variant_items, str):
		variant_items = json.loads(variant_items)

	for item in variant_items:
		args = frappe._dict(
			{
				"item_code": item.get("variant_item_code"),
				"required_qty": item.get("qty"),
				"qty": item.get("qty"),  # for bom
				"source_warehouse": item.get("source_warehouse"),
				"operation": item.get("operation"),
			}
		)

		bom_doc = frappe.get_cached_doc("BOM", bom_no)
		item_data = get_item_details(args.item_code, skip_bom_info=True)
		args.update(item_data)

		args["rate"] = get_bom_item_rate(
			{
				"company": wo_doc.company,
				"item_code": args.get("item_code"),
				"qty": args.get("required_qty"),
				"uom": args.get("stock_uom"),
				"stock_uom": args.get("stock_uom"),
				"conversion_factor": 1,
			},
			bom_doc,
		)

		if not args.source_warehouse:
			args["source_warehouse"] = get_item_defaults(
				item.get("variant_item_code"), wo_doc.company
			).default_warehouse

		args["amount"] = flt(args.get("required_qty")) * flt(args.get("rate"))
		args["uom"] = item_data.stock_uom

		existing_row = (
			get_template_rm_item(wo_doc, item.get("item_code")) if table_name == "required_items" else None
		)
		if existing_row:
			existing_row.update(args)
		else:
			wo_doc.append(table_name, args)


def get_template_rm_item(wo_doc, item_code):
	for row in wo_doc.required_items:
		if row.item_code == item_code:
			return row


@frappe.whitelist()
def check_if_scrap_warehouse_mandatory(bom_no):
	res = {"set_scrap_wh_mandatory": False}
	if bom_no:
		bom = frappe.get_doc("BOM", bom_no)

		if len(bom.scrap_items) > 0:
			res["set_scrap_wh_mandatory"] = True

	return res


@frappe.whitelist()
def set_work_order_ops(name):
	po = frappe.get_doc("Work Order", name)
	po.set_work_order_operations()
	po.save()


@frappe.whitelist()
def make_stock_entry(work_order_id, purpose, qty=None, target_warehouse=None):
	work_order = frappe.get_doc("Work Order", work_order_id)
	if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
		wip_warehouse = work_order.wip_warehouse
	else:
		wip_warehouse = None

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = purpose
	stock_entry.work_order = work_order_id
	stock_entry.company = work_order.company
	stock_entry.from_bom = 1
	stock_entry.bom_no = work_order.bom_no
	stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
	# accept 0 qty as well
	stock_entry.fg_completed_qty = (
		qty if qty is not None else (flt(work_order.qty) - flt(work_order.produced_qty))
	)

	if work_order.bom_no:
		stock_entry.inspection_required = frappe.db.get_value("BOM", work_order.bom_no, "inspection_required")

	if purpose == "Material Transfer for Manufacture":
		stock_entry.to_warehouse = wip_warehouse
		stock_entry.project = work_order.project
	else:
		stock_entry.from_warehouse = (
			work_order.source_warehouse
			if work_order.skip_transfer and not work_order.from_wip_warehouse
			else wip_warehouse
		)
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.project = work_order.project

	if purpose == "Disassemble":
		stock_entry.from_warehouse = work_order.fg_warehouse
		stock_entry.to_warehouse = target_warehouse or work_order.source_warehouse

	stock_entry.set_stock_entry_type()
	stock_entry.get_items()

	if purpose != "Disassemble":
		stock_entry.set_serial_no_batch_for_finished_good()

	return stock_entry.as_dict()


@frappe.whitelist()
def get_default_warehouse():
	doc = frappe.get_cached_doc("Manufacturing Settings")

	return {
		"wip_warehouse": doc.default_wip_warehouse,
		"fg_warehouse": doc.default_fg_warehouse,
		"scrap_warehouse": doc.default_scrap_warehouse,
	}


@frappe.whitelist()
def stop_unstop(work_order, status):
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
def query_sales_order(production_item):
	out = frappe.db.sql_list(
		"""
		select distinct so.name from `tabSales Order` so, `tabSales Order Item` so_item
		where so_item.parent=so.name and so_item.item_code=%s and so.docstatus=1
	union
		select distinct so.name from `tabSales Order` so, `tabPacked Item` pi_item
		where pi_item.parent=so.name and pi_item.item_code=%s and so.docstatus=1
	""",
		(production_item, production_item),
	)

	return out


@frappe.whitelist()
def make_job_card(work_order, operations):
	if isinstance(operations, str):
		operations = json.loads(operations)

	work_order = frappe.get_doc("Work Order", work_order)
	for row in operations:
		row = frappe._dict(row)
		validate_operation_data(row)
		qty = row.get("qty")
		while qty > 0:
			qty = split_qty_based_on_batch_size(work_order, row, qty)
			if row.job_card_qty > 0:
				create_job_card(work_order, row, auto_create=True)


@frappe.whitelist()
def close_work_order(work_order, status):
	if not frappe.has_permission("Work Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	work_order = frappe.get_doc("Work Order", work_order)
	if work_order.get("operations"):
		job_cards = frappe.get_list(
			"Job Card", filters={"work_order": work_order.name, "status": "Work In Progress"}, pluck="name"
		)

		if job_cards:
			job_cards = ", ".join(job_cards)
			frappe.throw(
				_("Can not close Work Order. Since {0} Job Cards are in Work In Progress state.").format(
					job_cards
				)
			)

	work_order.update_status(status)
	work_order.update_planned_qty()
	frappe.msgprint(_("Work Order has been {0}").format(status))
	work_order.notify_update()
	return work_order.status


def split_qty_based_on_batch_size(wo_doc, row, qty):
	if not cint(frappe.db.get_value("Operation", row.operation, "create_job_card_based_on_batch_size")):
		row.batch_size = row.get("qty") or wo_doc.qty

	row.job_card_qty = row.batch_size
	if row.batch_size and qty >= row.batch_size:
		qty -= row.batch_size
	elif qty > 0:
		row.job_card_qty = qty
		qty = 0

	get_serial_nos_for_job_card(row, wo_doc)

	return qty


def get_serial_nos_for_job_card(row, wo_doc):
	if not wo_doc.has_serial_no:
		return

	serial_nos = get_serial_nos_for_work_order(wo_doc.name, wo_doc.production_item)
	used_serial_nos = []
	for d in frappe.get_all(
		"Job Card",
		fields=["serial_no"],
		filters={"docstatus": ("<", 2), "work_order": wo_doc.name, "operation_id": row.name},
	):
		used_serial_nos.extend(get_serial_nos(d.serial_no))

	serial_nos = sorted(list(set(serial_nos) - set(used_serial_nos)))
	row.serial_no = "\n".join(serial_nos[0 : cint(row.job_card_qty)])


def get_serial_nos_for_work_order(work_order, production_item):
	serial_nos = []
	for d in frappe.get_all(
		"Serial No",
		fields=["name"],
		filters={
			"work_order": work_order,
			"item_code": production_item,
		},
	):
		serial_nos.append(d.name)

	return serial_nos


def validate_operation_data(row):
	if flt(row.get("qty")) <= 0:
		frappe.throw(
			_("Quantity to Manufacture can not be zero for the operation {0}").format(
				frappe.bold(row.get("operation"))
			)
		)

	if flt(row.get("qty")) > flt(row.get("pending_qty")):
		frappe.throw(
			_("For operation {0}: Quantity ({1}) can not be greter than pending quantity({2})").format(
				frappe.bold(row.get("operation")),
				frappe.bold(row.get("qty")),
				frappe.bold(row.get("pending_qty")),
			)
		)


def create_job_card(work_order, row, enable_capacity_planning=False, auto_create=False):
	doc = frappe.new_doc("Job Card")
	doc.update(
		{
			"work_order": work_order.name,
			"workstation_type": row.get("workstation_type"),
			"operation": row.get("operation"),
			"workstation": row.get("workstation"),
			"posting_date": nowdate(),
			"for_quantity": row.job_card_qty or work_order.get("qty", 0),
			"operation_id": row.get("name"),
			"bom_no": work_order.bom_no,
			"project": work_order.project,
			"company": work_order.company,
			"sequence_id": row.get("sequence_id"),
			"wip_warehouse": work_order.wip_warehouse,
			"hour_rate": row.get("hour_rate"),
			"serial_no": row.get("serial_no"),
		}
	)

	if work_order.transfer_material_against == "Job Card" and not work_order.skip_transfer:
		doc.get_required_items()

	if auto_create:
		doc.flags.ignore_mandatory = True
		if enable_capacity_planning:
			doc.schedule_time_logs(row)

		doc.insert()
		frappe.msgprint(_("Job card {0} created").format(get_link_to_form("Job Card", doc.name)), alert=True)

	if enable_capacity_planning:
		# automatically added scheduling rows shouldn't change status to WIP
		doc.db_set("status", "Open")

	return doc


def get_work_order_operation_data(work_order, operation, workstation):
	for d in work_order.operations:
		if d.operation == operation and d.workstation == workstation:
			return d


@frappe.whitelist()
def create_pick_list(source_name, target_doc=None, for_qty=None):
	for_qty = for_qty or json.loads(target_doc).get("for_qty")
	max_finished_goods_qty = frappe.db.get_value("Work Order", source_name, "qty")

	def update_item_quantity(source, target, source_parent):
		pending_to_issue = flt(source.required_qty) - flt(source.transferred_qty)
		desire_to_transfer = flt(source.required_qty) / max_finished_goods_qty * flt(for_qty)

		qty = 0
		if desire_to_transfer <= pending_to_issue:
			qty = desire_to_transfer
		elif pending_to_issue > 0:
			qty = pending_to_issue

		if qty:
			target.qty = qty
			target.stock_qty = qty
			target.uom = frappe.get_value("Item", source.item_code, "stock_uom")
			target.stock_uom = target.uom
			target.conversion_factor = 1
		else:
			target.delete()

	doc = get_mapped_doc(
		"Work Order",
		source_name,
		{
			"Work Order": {"doctype": "Pick List", "validation": {"docstatus": ["=", 1]}},
			"Work Order Item": {
				"doctype": "Pick List Item",
				"postprocess": update_item_quantity,
				"condition": lambda doc: abs(doc.transferred_qty) < abs(doc.required_qty),
			},
		},
		target_doc,
	)

	doc.for_qty = for_qty

	doc.set_item_locations()

	return doc


def get_reserved_qty_for_production(
	item_code: str,
	warehouse: str,
	non_completed_production_plans: list | None = None,
	check_production_plan: bool = False,
) -> float:
	"""Get total reserved quantity for any item in specified warehouse"""
	wo = frappe.qb.DocType("Work Order")
	wo_item = frappe.qb.DocType("Work Order Item")

	if check_production_plan:
		qty_field = wo_item.required_qty
	else:
		qty_field = Case()
		qty_field = qty_field.when(wo.skip_transfer == 0, wo_item.required_qty - wo_item.transferred_qty)
		qty_field = qty_field.else_(wo_item.required_qty - wo_item.consumed_qty)

	query = (
		frappe.qb.from_(wo)
		.from_(wo_item)
		.select(Sum(qty_field))
		.where(
			(wo_item.item_code == item_code)
			& (wo_item.parent == wo.name)
			& (wo.docstatus == 1)
			& (wo_item.source_warehouse == warehouse)
		)
	)

	if check_production_plan:
		query = query.where(wo.production_plan.isnotnull())
	else:
		query = query.where(
			(wo.status.notin(["Stopped", "Completed", "Closed"]))
			& (
				(wo_item.required_qty > wo_item.transferred_qty)
				| (wo_item.required_qty > wo_item.consumed_qty)
			)
		)

	if non_completed_production_plans:
		query = query.where(wo.production_plan.isin(non_completed_production_plans))

	return query.run()[0][0] or 0.0


@frappe.whitelist()
def make_stock_return_entry(work_order):
	from erpnext.stock.doctype.stock_entry.stock_entry import get_available_materials

	non_consumed_items = get_available_materials(work_order)
	if not non_consumed_items:
		return

	wo_doc = frappe.get_cached_doc("Work Order", work_order)

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.from_bom = 1
	stock_entry.is_return = 1
	stock_entry.work_order = work_order
	stock_entry.purpose = "Material Transfer for Manufacture"
	stock_entry.bom_no = wo_doc.bom_no
	stock_entry.add_transfered_raw_materials_in_items()
	stock_entry.set_stock_entry_type()

	return stock_entry

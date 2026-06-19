# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom.bom import validate_bom_no

# Backward-compatible re-exports (moved to mapper.py / services/).
from erpnext.manufacturing.doctype.production_plan.mapper import (
	get_so_details,
	sales_order_query,
)
from erpnext.manufacturing.doctype.production_plan.services.material_request import (
	MaterialRequestService,
	download_raw_materials,
	get_bin_details,
	get_exploded_items,
	get_item_data,
	get_items_for_material_requests,
	get_material_request_items,
	get_materials_from_other_locations,
	get_raw_materials_of_sub_assembly_items,
	get_sales_orders,
	get_subitems,
	get_uom_conversion_factor,
	get_warehouse_list,
	set_default_warehouses,
)
from erpnext.manufacturing.doctype.production_plan.services.reservation import (
	cancel_stock_reservation_entries,
	get_non_completed_production_plans,
	get_reserved_qty_for_production_plan,
	get_reserved_qty_for_sub_assembly,
	make_stock_reservation_entries,
	reserve_stock_for_production_plan,
)
from erpnext.manufacturing.doctype.production_plan.services.sales_order_planning import (
	SalesOrderSourcingService,
)
from erpnext.manufacturing.doctype.production_plan.services.sub_assembly import (
	SubAssemblyService,
)
from erpnext.manufacturing.doctype.production_plan.services.work_order_planning import (
	WorkOrderCreationService,
)
from erpnext.stock.utils import get_or_make_bin
from erpnext.utilities.transaction_base import validate_uom_is_integer


class ProductionPlan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.material_request_plan_item.material_request_plan_item import (
			MaterialRequestPlanItem,
		)
		from erpnext.manufacturing.doctype.production_plan_item.production_plan_item import ProductionPlanItem
		from erpnext.manufacturing.doctype.production_plan_item_reference.production_plan_item_reference import (
			ProductionPlanItemReference,
		)
		from erpnext.manufacturing.doctype.production_plan_material_request.production_plan_material_request import (
			ProductionPlanMaterialRequest,
		)
		from erpnext.manufacturing.doctype.production_plan_material_request_warehouse.production_plan_material_request_warehouse import (
			ProductionPlanMaterialRequestWarehouse,
		)
		from erpnext.manufacturing.doctype.production_plan_sales_order.production_plan_sales_order import (
			ProductionPlanSalesOrder,
		)
		from erpnext.manufacturing.doctype.production_plan_sub_assembly_item.production_plan_sub_assembly_item import (
			ProductionPlanSubAssemblyItem,
		)

		amended_from: DF.Link | None
		combine_items: DF.Check
		combine_sub_items: DF.Check
		company: DF.Link
		consider_minimum_order_qty: DF.Check
		customer: DF.Link | None
		for_warehouse: DF.Link | None
		from_date: DF.Date | None
		from_delivery_date: DF.Date | None
		get_items_from: DF.Literal["", "Sales Order", "Material Request"]
		ignore_existing_ordered_qty: DF.Check
		include_non_stock_items: DF.Check
		include_safety_stock: DF.Check
		include_subcontracted_items: DF.Check
		item_code: DF.Link | None
		material_requests: DF.Table[ProductionPlanMaterialRequest]
		mr_items: DF.Table[MaterialRequestPlanItem]
		naming_series: DF.Literal["MFG-PP-.YYYY.-"]
		po_items: DF.Table[ProductionPlanItem]
		posting_date: DF.Date
		prod_plan_references: DF.Table[ProductionPlanItemReference]
		project: DF.Link | None
		reserve_stock: DF.Check
		sales_order_status: DF.Literal["", "To Deliver and Bill", "To Bill", "To Deliver"]
		sales_orders: DF.Table[ProductionPlanSalesOrder]
		skip_available_sub_assembly_item: DF.Check
		status: DF.Literal[
			"",
			"Draft",
			"Submitted",
			"Not Started",
			"In Process",
			"Completed",
			"Closed",
			"Cancelled",
			"Material Requested",
		]
		sub_assembly_items: DF.Table[ProductionPlanSubAssemblyItem]
		sub_assembly_warehouse: DF.Link | None
		to_date: DF.Date | None
		to_delivery_date: DF.Date | None
		total_planned_qty: DF.Float
		total_produced_qty: DF.Float
		warehouse: DF.Link | None
		warehouses: DF.TableMultiSelect[ProductionPlanMaterialRequestWarehouse]
	# end: auto-generated types

	def onload(self):
		self.set_onload(
			"enable_stock_reservation",
			frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"),
		)

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def validate(self):
		self.set_pending_qty_in_row_without_reference()
		self.calculate_total_planned_qty()
		self.set_status()
		self._rename_temporary_references()
		validate_uom_is_integer(self, "stock_uom", "planned_qty")
		self.validate_sales_orders()
		self.validate_material_request_type()
		self.enable_auto_reserve_stock()

	def enable_auto_reserve_stock(self):
		if self.is_new() and frappe.db.get_single_value("Stock Settings", "auto_reserve_stock"):
			self.reserve_stock = 1

	def validate_material_request_type(self):
		for row in self.get("mr_items"):
			if row.from_warehouse and row.material_request_type != "Material Transfer":
				row.from_warehouse = ""

	@frappe.whitelist()
	def validate_sales_orders(self, sales_order: str | None = None):
		sales_orders = []

		if sales_order:
			sales_orders.append(sales_order)
		else:
			sales_orders = [row.sales_order for row in self.sales_orders if row.sales_order]

		data = sales_order_query(filters={"company": self.company, "sales_orders": sales_orders})

		title = _("Production Plan Already Submitted")
		if not data and sales_orders:
			msg = _("No items are available in the sales order {0} for production").format(sales_orders[0])
			if len(sales_orders) > 1:
				sales_orders = ", ".join(sales_orders)
				msg = _("No items are available in sales orders {0} for production").format(sales_orders)

			frappe.throw(msg, title=title)

		data = [d[0] for d in data]

		for sales_order in sales_orders:
			if sales_order not in data:
				frappe.throw(
					_("No items are available in the sales order {0} for production").format(sales_order),
					title=title,
				)

	def set_pending_qty_in_row_without_reference(self):
		"Set Pending Qty in independent rows (not from SO or MR)."
		if self.docstatus > 0:  # set only to initialise value before submit
			return

		for item in self.po_items:
			if not item.get("sales_order") or not item.get("material_request"):
				item.pending_qty = item.planned_qty

	def calculate_total_planned_qty(self):
		self.total_planned_qty = 0
		for d in self.po_items:
			self.total_planned_qty += flt(d.planned_qty)

	def validate_data(self):
		for d in self.get("po_items"):
			if not d.bom_no:
				frappe.throw(_("Please select BOM for Item in Row {0}").format(d.idx))
			else:
				validate_bom_no(d.item_code, d.bom_no)

			if not flt(d.planned_qty):
				frappe.throw(_("Please enter Planned Qty for Item {0} at row {1}").format(d.item_code, d.idx))

	def _rename_temporary_references(self):
		"""po_items and sub_assembly_items items are both constructed client side without saving.

		Attempt to fix linkages by using temporary names to map final row names.
		"""
		new_name_map = {d.temporary_name: d.name for d in self.po_items if d.temporary_name}
		actual_names = {d.name for d in self.po_items}

		for sub_assy in self.sub_assembly_items:
			if sub_assy.production_plan_item not in actual_names:
				sub_assy.production_plan_item = new_name_map.get(sub_assy.production_plan_item)

	def calculate_total_produced_qty(self):
		self.total_produced_qty = 0
		for d in self.po_items:
			self.total_produced_qty += flt(d.produced_qty)

		self.db_set("total_produced_qty", self.total_produced_qty, update_modified=False)

	def update_produced_pending_qty(self, produced_qty, production_plan_item):
		for data in self.po_items:
			if data.name == production_plan_item:
				data.produced_qty = produced_qty
				data.pending_qty = flt(data.planned_qty - produced_qty)
				data.db_update()

		self.calculate_total_produced_qty()
		self.set_status()
		self.db_set("status", self.status)

	def on_submit(self):
		self.update_bin_qty()
		self.update_sales_order()
		self.add_reference_to_raw_materials()
		self.update_stock_reservation()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.delete_draft_work_order()
		self.update_bin_qty()
		self.update_sales_order()
		self.update_stock_reservation()

	def update_stock_reservation(self):
		if not self.reserve_stock:
			return

		reserve_stock_for_production_plan(self)

	def add_reference_to_raw_materials(self):
		for item in self.mr_items:
			if reference := next(
				(
					sa_item.name
					for sa_item in self.sub_assembly_items
					if sa_item.production_item == item.main_item_code and sa_item.bom_no == item.from_bom
				),
				None,
			):
				item.db_set("sub_assembly_item_reference", reference)
			elif (
				self.reserve_stock
				and item.main_item_code
				and item.from_bom
				and item.main_item_code != frappe.get_cached_value("BOM", item.from_bom, "item")
			):
				frappe.throw(
					_(
						"Sub assembly item references are missing. Please fetch the sub assemblies and raw materials again."
					)
				)

	def update_sales_order(self):
		sales_orders = [row.sales_order for row in self.po_items if row.sales_order]
		if sales_orders:
			so_wise_planned_qty = self.get_so_wise_planned_qty(sales_orders)

			for row in self.po_items:
				if not row.sales_order and not row.sales_order_item:
					continue

				key = (row.sales_order, row.sales_order_item)
				frappe.db.set_value(
					"Sales Order Item",
					row.sales_order_item,
					"production_plan_qty",
					flt(so_wise_planned_qty.get(key)),
				)

	@staticmethod
	def get_so_wise_planned_qty(sales_orders):
		so_wise_planned_qty = frappe._dict()
		data = frappe.get_all(
			"Production Plan Item",
			fields=["sales_order", "sales_order_item", {"SUM": "planned_qty", "as": "qty"}],
			filters={
				"sales_order": ("in", sales_orders),
				"docstatus": 1,
				"sales_order_item": ("is", "set"),
			},
			group_by="sales_order, sales_order_item",
		)

		for row in data:
			key = (row.sales_order, row.sales_order_item)
			so_wise_planned_qty[key] = row.qty

		return so_wise_planned_qty

	def update_bin_qty(self):
		for d in self.mr_items:
			if d.warehouse:
				bin_name = get_or_make_bin(d.item_code, d.warehouse)
				bin = frappe.get_doc("Bin", bin_name, for_update=True)
				bin.update_reserved_qty_for_production_plan()

		for d in self.sub_assembly_items:
			if d.fg_warehouse and d.type_of_manufacturing == "In House":
				bin_name = get_or_make_bin(d.production_item, d.fg_warehouse)
				bin = frappe.get_doc("Bin", bin_name, for_update=True)
				bin.update_reserved_qty_for_for_sub_assembly()

	def delete_draft_work_order(self):
		for d in frappe.get_all(
			"Work Order", fields=["name"], filters={"docstatus": 0, "production_plan": ("=", self.name)}
		):
			frappe.delete_doc("Work Order", d.name)

	@frappe.whitelist()
	def set_status(self, close: bool | None = None, update_bin: bool = False):
		self.status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(self.docstatus)

		if close:
			self.db_set("status", "Closed")
			self.update_bin_qty()
			return

		if self.total_produced_qty > 0:
			self.status = "In Process"
			if self.all_items_completed():
				self.status = "Completed"

		if self.status != "Completed":
			self.update_requested_status()
			self.update_ordered_status()

		if close is not None:
			self.db_set("status", self.status)

		if update_bin and self.docstatus == 1 and self.status != "Completed":
			self.update_bin_qty()

	def update_ordered_status(self):
		for child_table in ["po_items", "sub_assembly_items"]:
			for item in self.get(child_table):
				if item.ordered_qty:
					self.status = "In Process"
					return

	def update_requested_status(self):
		for d in self.mr_items:
			if d.requested_qty:
				self.status = "Material Requested"
				break

	def get_production_items(self):
		return WorkOrderCreationService(self).get_production_items()

	@frappe.whitelist()
	def make_work_order(self):
		return WorkOrderCreationService(self).make_work_order()

	def make_work_order_for_finished_goods(self, wo_list, default_warehouses):
		return WorkOrderCreationService(self).make_work_order_for_finished_goods(wo_list, default_warehouses)

	def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
		return WorkOrderCreationService(self).make_work_order_for_subassembly_items(
			wo_list, subcontracted_po, default_warehouses
		)

	def prepare_data_for_sub_assembly_items(self, row, wo_data):
		return WorkOrderCreationService(self).prepare_data_for_sub_assembly_items(row, wo_data)

	def make_subcontracted_purchase_order(self, subcontracted_po, purchase_orders):
		return WorkOrderCreationService(self).make_subcontracted_purchase_order(
			subcontracted_po, purchase_orders
		)

	def show_list_created_message(self, doctype, doc_list=None):
		return WorkOrderCreationService(self).show_list_created_message(doctype, doc_list)

	def create_work_order(self, item):
		return WorkOrderCreationService(self).create_work_order(item)

	@frappe.whitelist()
	def get_open_sales_orders(self):
		return SalesOrderSourcingService(self).get_open_sales_orders()

	def add_so_in_table(self, open_so):
		return SalesOrderSourcingService(self).add_so_in_table(open_so)

	@frappe.whitelist()
	def get_pending_material_requests(self):
		return SalesOrderSourcingService(self).get_pending_material_requests()

	def add_mr_in_table(self, pending_mr):
		return SalesOrderSourcingService(self).add_mr_in_table(pending_mr)

	@frappe.whitelist()
	def combine_so_items(self):
		return SalesOrderSourcingService(self).combine_so_items()

	@frappe.whitelist()
	def get_items(self):
		return SalesOrderSourcingService(self).get_items()

	def get_so_mr_list(self, field, table):
		return SalesOrderSourcingService(self).get_so_mr_list(field, table)

	def get_bom_item_condition(self):
		return SalesOrderSourcingService(self).get_bom_item_condition()

	def get_so_items(self):
		return SalesOrderSourcingService(self).get_so_items()

	def get_mr_items(self):
		return SalesOrderSourcingService(self).get_mr_items()

	def add_items(self, items):
		return SalesOrderSourcingService(self).add_items(items)

	def add_pp_ref(self, refs):
		return SalesOrderSourcingService(self).add_pp_ref(refs)

	def validate_mr_subcontracted(self):
		return MaterialRequestService(self).validate_mr_subcontracted()

	@frappe.whitelist()
	def make_material_request(self):
		return MaterialRequestService(self).make_material_request()

	@frappe.whitelist()
	def get_sub_assembly_items(self, manufacturing_type: str | None = None):
		return SubAssemblyService(self).get_sub_assembly_items(manufacturing_type=manufacturing_type)

	def set_sub_assembly_items_based_on_level(self, row, bom_data, manufacturing_type=None):
		return SubAssemblyService(self).set_sub_assembly_items_based_on_level(
			row, bom_data, manufacturing_type
		)

	def set_default_supplier_for_subcontracting_order(self):
		return SubAssemblyService(self).set_default_supplier_for_subcontracting_order()

	def combine_subassembly_items(self, sub_assembly_items_store):
		return SubAssemblyService(self).combine_subassembly_items(sub_assembly_items_store)

	def all_items_completed(self):
		return SubAssemblyService(self).all_items_completed()

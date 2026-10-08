# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import IfNull, Sum
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
from erpnext.manufacturing.doctype.production_plan.services.work_order_quantities import (
	ProductionPlanWorkOrderQuantities,
)
from erpnext.stock.utils import get_or_make_bin, validate_warehouse_company
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
		no_of_shifts: DF.Int
		po_items: DF.Table[ProductionPlanItem]
		posting_date: DF.Date
		prod_plan_references: DF.Table[ProductionPlanItemReference]
		project: DF.Link | None
		raw_material_group_warehouse: DF.Link | None
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
		if self.docstatus == 1:
			self.set_onload(
				"pending_work_order_qty",
				ProductionPlanWorkOrderQuantities(self.name).get_pending_quantities(self),
			)

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def validate(self):
		self.set_pending_qty_in_row_without_reference()
		self.calculate_total_planned_qty()
		self.set_status()
		self._rename_temporary_references()
		validate_uom_is_integer(self, "stock_uom", "planned_qty")
		self.validate_data()
		self.validate_sales_orders()
		self.validate_material_request_type()
		self.validate_raw_material_group_warehouse()
		if self.for_warehouse:
			validate_warehouse_company(self.for_warehouse, self.company)
		self.enable_auto_reserve_stock()

	def validate_raw_material_group_warehouse(self):
		if not self.raw_material_group_warehouse:
			return

		group = frappe.db.get_value(
			"Warehouse",
			{"name": self.raw_material_group_warehouse, "is_group": 1, "company": self.company},
			["lft", "rgt"],
			as_dict=True,
		)
		if not group:
			frappe.throw(
				_("{0} must be a group warehouse of company {1}.").format(
					frappe.bold(_("Raw Material Group Warehouse")), frappe.bold(self.company)
				)
			)

		if self.for_warehouse and not frappe.db.exists(
			"Warehouse",
			{"name": self.for_warehouse, "is_group": 0, "lft": (">", group.lft), "rgt": ("<", group.rgt)},
		):
			frappe.throw(
				_("For Warehouse {0} must be a non-group warehouse under {1}.").format(
					frappe.bold(self.for_warehouse), frappe.bold(self.raw_material_group_warehouse)
				)
			)

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
		validated_boms = set()
		for d in self.get("po_items"):
			if not d.bom_no:
				frappe.throw(_("Please select BOM for Item in Row {0}").format(d.idx))
			elif (d.item_code, d.bom_no) not in validated_boms:
				validate_bom_no(d.item_code, d.bom_no)
				validated_boms.add((d.item_code, d.bom_no))

			if flt(d.planned_qty) <= 0:
				frappe.throw(
					_("Row #{0}: Planned Qty must be greater than 0 for Item {1}.").format(
						d.idx, frappe.bold(d.item_code)
					)
				)

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
		self.update_status_and_bin_qty()

	def update_status_and_bin_qty(self):
		previous_status = self.status
		self.set_status()
		self.db_set("status", self.status)
		if previous_status != self.status and "Completed" in (previous_status, self.status):
			self.update_bin_qty()

	def before_submit(self):
		self.validate_combined_sales_order_quantities()
		quantities = self.get_sales_order_plan_quantities()
		items = self.lock_sales_order_items(quantities)
		precision = frappe.get_precision("Sales Order Item", "stock_qty")
		allowance = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_sales_order")
		)
		for key, qty in quantities.items():
			item = items[key]
			if not frappe.get_cached_value("Item", item.item_code, "is_stock_item"):
				continue
			remaining = flt(
				flt(item.stock_qty) * (1 + allowance / 100) - flt(item.production_plan_qty), precision
			)
			if flt(qty, precision) > remaining:
				frappe.throw(
					_(
						"Item {0} in Sales Order {1}: Planned Qty {2} exceeds the unplanned quantity {3}."
					).format(item.item_code, key[0], qty, max(0, remaining)),
					title=_("Sales Order Quantity Exceeded"),
				)

	def before_cancel(self):
		self.lock_sales_order_items(self.get_sales_order_plan_quantities())

	def validate_combined_sales_order_quantities(self):
		if not self.combine_items or self.get_items_from != "Sales Order":
			return

		reference_quantities = {}
		for row in self.prod_plan_references:
			if not (row.sales_order and row.sales_order_item and row.item_reference) or flt(row.qty) <= 0:
				frappe.throw(_("Invalid combined Sales Order references. Please fetch items again."))
			reference_quantities[row.item_reference] = reference_quantities.get(row.item_reference, 0) + flt(
				row.qty
			)

		planned_quantities = {}
		for row in self.po_items:
			if row.sales_order_item:
				planned_quantities[row.sales_order_item] = planned_quantities.get(
					row.sales_order_item, 0
				) + flt(row.planned_qty)

		precision = frappe.get_precision("Sales Order Item", "stock_qty")
		if reference_quantities.keys() != planned_quantities.keys() or any(
			flt(qty, precision) != flt(planned_quantities[key], precision)
			for key, qty in reference_quantities.items()
		):
			frappe.throw(
				_(
					"Combined planned quantities must match their Sales Order references. Please fetch items again."
				),
				title=_("Combined Quantity Mismatch"),
			)

	def get_sales_order_plan_quantities(self):
		quantities = {}
		combined = self.combine_items and self.prod_plan_references
		rows = self.prod_plan_references if combined else self.po_items
		for row in rows:
			if row.sales_order and row.sales_order_item:
				key = (row.sales_order, row.sales_order_item)
				qty = row.qty if combined else row.planned_qty
				quantities[key] = quantities.get(key, 0) + flt(qty)
		return quantities

	def lock_sales_order_items(self, quantities):
		items = {}
		# Plans for different lines of one order must also serialize their quantity rollups.
		for sales_order in sorted({key[0] for key in quantities}):
			company = frappe.db.get_value("Sales Order", sales_order, "company", for_update=True)
			if company != self.company:
				frappe.throw(
					_("Sales Order {0} must belong to Company {1}.").format(sales_order, self.company)
				)
		for sales_order, item_name in sorted(quantities):
			item = frappe.db.get_value(
				"Sales Order Item",
				{"name": item_name, "parent": sales_order},
				["item_code", "stock_qty", "production_plan_qty"],
				as_dict=True,
				for_update=True,
			)
			if not item:
				frappe.throw(_("Invalid Sales Order item reference {0}.").format(item_name))
			items[sales_order, item_name] = item
		return items

	def on_submit(self):
		self.update_bin_qty()
		self.update_sales_order()
		self.add_reference_to_raw_materials()
		self.update_stock_reservation()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.delete_draft_work_order()
		self.delete_production_plan_schedule()
		self.update_bin_qty()
		self.update_sales_order()
		self.update_stock_reservation()
		self.delete_sub_assembly_and_material_rows()

	def delete_production_plan_schedule(self):
		frappe.db.delete("Production Plan Schedule", {"production_plan": self.name})

	def delete_sub_assembly_and_material_rows(self):
		for doctype in ("Production Plan Sub Assembly Item", "Material Request Plan Item"):
			frappe.db.delete(doctype, {"parent": self.name, "parenttype": "Production Plan"})

		self.set("sub_assembly_items", [])
		self.set("mr_items", [])

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
		quantities = self.get_sales_order_plan_quantities()
		so_item = frappe.qb.DocType("Sales Order Item")
		item = frappe.qb.DocType("Item")
		stock_items = frappe.qb.from_(item).select(item.name).where(item.is_stock_item == 1)
		for (sales_order, item_name), qty in quantities.items():
			# The submit/cancel hooks hold the order locks. Avoid locking other plans' children.
			change = qty if self.docstatus == 1 else -qty
			planned_qty = IfNull(so_item.production_plan_qty, 0) + change
			if self.docstatus == 2:
				planned_qty = frappe.qb.terms.Case().when(planned_qty < 0, 0).else_(planned_qty)
			(
				frappe.qb.update(so_item)
				.set(so_item.production_plan_qty, planned_qty)
				# Packed-component quantities are not in the parent bundle's UOM.
				.where(
					(so_item.name == item_name)
					& (so_item.parent == sales_order)
					& so_item.item_code.isin(stock_items)
				)
			).run()

	@staticmethod
	def get_so_wise_planned_qty(sales_orders):
		so_wise_planned_qty = frappe._dict()
		if not sales_orders:
			return so_wise_planned_qty

		so_item = frappe.qb.DocType("Sales Order Item")
		item = frappe.qb.DocType("Item")
		stock_order_items = (
			frappe.qb.from_(so_item)
			.inner_join(item)
			.on(so_item.item_code == item.name)
			.select(so_item.name)
			.where((so_item.parent.isin(sales_orders)) & (item.is_stock_item == 1))
		)

		for doctype, qty_field in (
			("Production Plan Item", "planned_qty"),
			("Production Plan Item Reference", "qty"),
		):
			row_table = frappe.qb.DocType(doctype)
			plan = frappe.qb.DocType("Production Plan")
			query = (
				frappe.qb.from_(row_table)
				.inner_join(plan)
				.on(row_table.parent == plan.name)
				.select(
					row_table.sales_order, row_table.sales_order_item, Sum(row_table[qty_field]).as_("qty")
				)
				.where(
					(row_table.sales_order.isin(sales_orders))
					& (row_table.docstatus == 1)
					& (plan.docstatus == 1)
					& row_table.sales_order_item.isin(stock_order_items)
				)
				.groupby(row_table.sales_order, row_table.sales_order_item)
			)
			if doctype == "Production Plan Item Reference":
				query = query.where(plan.combine_items == 1)
			data = query.run(as_dict=True)
			for row in data:
				key = (row.sales_order, row.sales_order_item)
				so_wise_planned_qty[key] = so_wise_planned_qty.get(key, 0) + flt(row.qty)

		return so_wise_planned_qty

	def update_bin_qty(self, item_codes: set[str] | None = None):
		rows = [(d.item_code, d.warehouse) for d in self.mr_items]
		rows += [
			(d.production_item, d.fg_warehouse)
			for d in self.sub_assembly_items
			if d.type_of_manufacturing == "In House"
		]
		for item_code, warehouse in rows:
			if warehouse and (item_codes is None or item_code in item_codes):
				bin_name = get_or_make_bin(item_code, warehouse)
				bin = frappe.get_doc("Bin", bin_name, for_update=True)
				bin.update_reserved_qty_for_production_plan()

	def delete_draft_work_order(self):
		for d in frappe.get_all(
			"Work Order", fields=["name"], filters={"docstatus": 0, "production_plan": ("=", self.name)}
		):
			frappe.delete_doc("Work Order", d.name)

	@frappe.whitelist()
	def set_status(self, close: bool | None = None, update_bin: bool = False):
		self.check_permission("write")

		if close is None and self.status == "Closed":
			return

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

# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Order
from frappe.utils import cint, flt, get_link_to_form, nowdate, nowtime

from erpnext.manufacturing.doctype.plant_floor.services.batch_plan import BatchPlan
from erpnext.manufacturing.doctype.plant_floor.services.setup_check import PlantSetupCheck
from erpnext.manufacturing.doctype.workstation_type.workstation_type import PACKING_MACHINE_MODELS


class PlantFloor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.plant_floor_material.plant_floor_material import PlantFloorMaterial
		from erpnext.manufacturing.doctype.plant_floor_packing_material.plant_floor_packing_material import (
			PlantFloorPackingMaterial,
		)
		from erpnext.manufacturing.doctype.plant_floor_stage.plant_floor_stage import PlantFloorStage

		batch_size: DF.Float
		company: DF.Link | None
		fg_warehouse: DF.Link | None
		floor_name: DF.Data | None
		formula_tolerance: DF.Percent
		materials: DF.Table[PlantFloorMaterial]
		packing_materials: DF.Table[PlantFloorPackingMaterial]
		production_item: DF.Link | None
		stages: DF.Table[PlantFloorStage]
		warehouse: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_warehouse(self.warehouse)
		self.validate_warehouse(self.fg_warehouse)
		self.validate_formula()
		self.set_row_numbers()

	def set_row_numbers(self):
		for table in ("stages", "materials", "packing_materials"):
			for idx, row in enumerate(self.get(table), start=1):
				row.idx = idx
		self.set_sequence_ids()

	def set_sequence_ids(self):
		if not any(stage.sequence_id for stage in self.stages):
			for stage in self.stages:
				stage.sequence_id = stage.idx

	def validate_warehouse(self, name):
		if not name:
			return

		warehouse = frappe.get_cached_value("Warehouse", name, ["is_group", "company"], as_dict=True)
		if warehouse.is_group:
			frappe.throw(_("Warehouse {0} is a group warehouse").format(frappe.bold(name)))

		if self.company and warehouse.company != self.company:
			frappe.throw(
				_("Warehouse {0} does not belong to company {1}").format(
					frappe.bold(name), frappe.bold(self.company)
				)
			)

	def validate_formula(self):
		items = [row.item_code for row in self.materials]
		if duplicates := {item for item in items if items.count(item) > 1}:
			frappe.throw(_("Raw material {0} is in the formula more than once").format(", ".join(duplicates)))

		if len([row for row in self.materials if row.is_balance_item]) > 1:
			frappe.throw(_("Only one raw material can be the balance item"))

	@property
	def setup_errors(self) -> list[str]:
		return PlantSetupCheck(self).get_errors()

	@property
	def machine_models(self) -> dict:
		return {name: row.machine_model for name, row in self.get_workstation_details().items()}

	@property
	def machine_warehouses(self) -> dict:
		return {name: row.warehouse for name, row in self.get_workstation_details().items()}

	def get_workstation_details(self):
		names = tuple(sorted({stage.workstation for stage in self.stages if stage.workstation}))
		if getattr(self, "_workstation_details", (None,))[0] != names:
			self._workstation_details = (names, get_workstation_details(names))
		return self._workstation_details[1]

	def is_packing_stage(self, stage) -> bool:
		return self.machine_models.get(stage.workstation) in PACKING_MACHINE_MODELS

	@property
	def stage_sequences(self) -> list[list]:
		sequences = {}
		for stage in self.stages:
			sequences.setdefault(cint(stage.sequence_id), []).append(stage)
		return [sequences[sequence_id] for sequence_id in sorted(sequences)]

	def get_batch_plan(self, qty: float | None = None) -> BatchPlan:
		return BatchPlan(self, qty)

	@frappe.whitelist(methods=["POST"])
	def make_work_order(self, qty: float | None = None):
		frappe.has_permission("Work Order", "create", throw=True)
		work_order = frappe.new_doc("Work Order")
		work_order.update(
			{
				"production_item": self.production_item,
				"plant_floor": self.name,
				"company": self.company,
				"qty": flt(qty) or self.batch_size,
			}
		)
		work_order.insert()
		return work_order

	@frappe.whitelist()
	def make_stock_entry(self, kwargs: str | dict):
		if isinstance(kwargs, str):
			kwargs = frappe.parse_json(kwargs)

		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.update(
			{
				"company": kwargs.company,
				"from_warehouse": kwargs.from_warehouse,
				"to_warehouse": kwargs.to_warehouse,
				"purpose": kwargs.purpose,
				"stock_entry_type": kwargs.purpose,
				"posting_date": nowdate(),
				"posting_time": nowtime(),
				"items": self.get_item_details(kwargs),
			}
		)

		stock_entry.set_missing_values()

		return stock_entry

	def get_item_details(self, kwargs) -> list[dict]:
		item_details = frappe.db.get_value(
			"Item", kwargs.item_code, ["item_name", "stock_uom", "item_group", "description"], as_dict=True
		)
		item_details.update(
			{
				"qty": kwargs.qty,
				"uom": item_details.stock_uom,
				"item_code": kwargs.item_code,
				"conversion_factor": 1,
				"s_warehouse": kwargs.from_warehouse,
				"t_warehouse": kwargs.to_warehouse,
			}
		)

		return [item_details]


@frappe.whitelist()
def get_stock_summary(
	warehouse: str, start: int = 0, item_code: str | None = None, item_group: str | None = None
):
	frappe.has_permission("Warehouse", doc=warehouse, throw=True)

	if item_code:
		frappe.has_permission("Item", doc=item_code, throw=True)

	if item_group:
		frappe.has_permission("Item Group", doc=item_group, throw=True)

	stock_details = get_stock_details(warehouse, start=start, item_code=item_code, item_group=item_group)

	max_count = 0.0
	for d in stock_details:
		d.actual_or_pending = (
			d.projected_qty + d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract
		)
		d.pending_qty = 0
		d.total_reserved = d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract
		if d.actual_or_pending > d.actual_qty:
			d.pending_qty = d.actual_or_pending - d.actual_qty

		d.max_count = max(d.actual_or_pending, d.actual_qty, d.total_reserved, max_count)
		max_count = d.max_count
		d.item_link = get_link_to_form("Item", d.item_code)

	return stock_details


def get_workstation_details(workstations):
	if not workstations:
		return {}

	workstation = frappe.qb.DocType("Workstation")
	workstation_type = frappe.qb.DocType("Workstation Type")
	rows = (
		frappe.qb.from_(workstation)
		.left_join(workstation_type)
		.on(workstation_type.name == workstation.workstation_type)
		.select(
			workstation.name,
			workstation.warehouse,
			workstation.workstation_type,
			workstation_type.machine_model,
		)
		.where(workstation.name.isin(workstations))
	).run(as_dict=True)
	return {row.name: row for row in rows}


def get_stock_details(warehouse, start=0, item_code=None, item_group=None):
	item_table = frappe.qb.DocType("Item")
	bin_table = frappe.qb.DocType("Bin")

	query = (
		frappe.qb.from_(bin_table)
		.inner_join(item_table)
		.on(bin_table.item_code == item_table.name)
		.select(
			bin_table.item_code,
			bin_table.actual_qty,
			bin_table.projected_qty,
			bin_table.reserved_qty,
			bin_table.reserved_qty_for_production,
			bin_table.reserved_qty_for_sub_contract,
			bin_table.reserved_qty_for_production_plan,
			bin_table.reserved_stock,
			item_table.item_name,
			item_table.item_group,
			item_table.image,
		)
		.where(bin_table.warehouse == warehouse)
		.limit(20)
		.offset(start)
		.orderby(bin_table.actual_qty, order=Order.desc)
	)

	if item_code:
		query = query.where(bin_table.item_code == item_code)

	if item_group:
		lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])
		item_group_table = frappe.qb.DocType("Item Group")
		query = query.where(
			item_table.item_group.isin(
				frappe.qb.from_(item_group_table)
				.select(item_group_table.name)
				.where((item_group_table.lft >= lft) & (item_group_table.rgt <= rgt))
			)
		)

	return query.run(as_dict=True)

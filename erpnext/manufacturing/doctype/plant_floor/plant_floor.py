# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

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

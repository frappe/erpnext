# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from pathlib import Path

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import flt

MACHINE_SHAPES = frappe.get_file_json(Path(__file__).with_name("machine_shapes.json"))
PACKING_MACHINE_MODELS = ("Filling Line", "Bagging Line")
DEFAULT_WORKSTATION_TYPES = Path(__file__).with_name("default_workstation_types.json")


class WorkstationType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.workstation_cost.workstation_cost import WorkstationCost
		from erpnext.manufacturing.doctype.workstation_type_shape.workstation_type_shape import (
			WorkstationTypeShape,
		)

		description: DF.SmallText | None
		hour_rate: DF.Currency
		machine_model: DF.Literal[
			"",
			"Mixer",
			"Steam Kettle",
			"Reactor",
			"Fermenter",
			"Mill",
			"Dryer",
			"Cooler",
			"Filling Line",
			"Bagging Line",
		]
		shapes: DF.Table[WorkstationTypeShape]
		workstation_costs: DF.Table[WorkstationCost]
		workstation_type: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_duplicate_operating_component()
		self.validate_shapes()

	@property
	def machine_shapes(self) -> list[dict]:
		if self.shapes:
			return [
				row.as_dict(no_default_fields=True, no_child_table_fields=True, no_private_properties=True)
				for row in self.shapes
			]
		return get_preset_shapes(self.machine_model)

	@frappe.whitelist(methods=["POST"])
	def copy_preset_shapes(self):
		self.set("shapes", get_preset_shapes(self.machine_model))

	def validate_shapes(self):
		for row in self.shapes:
			for field in MACHINE_SHAPES["shapes"].get(row.shape, {}).get("size", {}):
				if flt(row.get(field)) <= 0:
					frappe.throw(
						_("Row {0}: {1} needs a {2} greater than zero").format(
							row.idx, _(row.shape), _(row.meta.get_label(field))
						)
					)

	def validate_duplicate_operating_component(self):
		components = []
		for row in self.workstation_costs:
			if row.operating_component not in components:
				components.append(row.operating_component)
			else:
				frappe.throw(
					_("Duplicate Operating Component {0} found in Operating Components").format(
						bold(row.operating_component)
					)
				)

	def before_save(self):
		self.set_hour_rate()

	def set_hour_rate(self):
		self.hour_rate = 0.0

		for row in self.workstation_costs:
			if row.operating_cost:
				self.hour_rate += flt(row.operating_cost)

	def on_update(self):
		self.update_workstation_costs()

	def update_workstation_costs(self):
		previous = self.get_doc_before_save()
		if not previous:
			return

		old_costs = get_cost_map(previous.workstation_costs)
		if old_costs == get_cost_map(self.workstation_costs):
			return

		for name in self.get_workstations_with_costs(old_costs):
			workstation = frappe.get_doc("Workstation", name)
			workstation.workstation_costs = []
			for row in self.workstation_costs:
				workstation.append(
					"workstation_costs",
					{"operating_component": row.operating_component, "operating_cost": row.operating_cost},
				)
			workstation.save()

	def get_workstations_with_costs(self, costs):
		workstation = frappe.qb.DocType("Workstation")
		cost = frappe.qb.DocType("Workstation Cost")
		rows = (
			frappe.qb.from_(workstation)
			.left_join(cost)
			.on((cost.parent == workstation.name) & (cost.parenttype == "Workstation"))
			.select(workstation.name, cost.operating_component, cost.operating_cost)
			.where(workstation.workstation_type == self.name)
			.run(as_dict=True)
		)

		workstation_costs = {}
		for row in rows:
			workstation_costs.setdefault(row.name, [])
			if row.operating_component:
				workstation_costs[row.name].append(row)

		return [name for name, rows in workstation_costs.items() if get_cost_map(rows) == costs]


def get_preset_shapes(machine_model: str | None = None) -> list[dict]:
	return [dict(row) for row in MACHINE_SHAPES["presets"].get(machine_model or "Machine", [])]


def get_cost_map(rows):
	return {row.operating_component: flt(row.operating_cost) for row in rows}


def get_workstations(workstation_type):
	workstations = frappe.get_all(
		"Workstation", filters={"workstation_type": workstation_type, "disabled": 0}, order_by="creation"
	)

	return [workstation.name for workstation in workstations]


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
			workstation.status,
			workstation.batch_capacity,
			workstation_type.machine_model,
		)
		.where(workstation.name.isin(workstations))
	).run(as_dict=True)
	return {row.name: row for row in rows}


def create_default_workstation_types():
	for values in frappe.get_file_json(DEFAULT_WORKSTATION_TYPES):
		if not frappe.db.exists("Workstation Type", values["workstation_type"]):
			frappe.get_doc({"doctype": "Workstation Type", **values}).insert(ignore_permissions=True)

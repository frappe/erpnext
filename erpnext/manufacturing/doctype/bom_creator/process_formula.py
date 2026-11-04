# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict
from functools import cached_property

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.manufacturing.doctype.workstation_type.workstation_type import (
	PACKING_MACHINE_MODELS,
	get_workstation_details,
)
from erpnext.stock.doctype.item.item import get_uom_conv_factor

WEIGHT_TOLERANCE = 0.001
QTY_PRECISION = 9


class ProcessFormula:
	def __init__(self, design):
		self.design = design
		self.stages = [row for row in design.operations if not cint(row.bom_node_id)]

	@cached_property
	def item(self):
		fields = ["item_name", "stock_uom", "weight_per_unit", "weight_uom"]
		return frappe.get_cached_value("Item", self.design.item_code, fields, as_dict=True) or frappe._dict()

	@property
	def packing_stage(self):
		return self.stages[-1] if self.stages else None

	@property
	def process_stages(self):
		return self.stages[:-1]

	@property
	def materials(self):
		return [
			row for row in self.design.materials if not cint(row.bom_node_id) and not row.from_operation_id
		]

	@property
	def raw_materials(self):
		packing_id = cint(self.packing_stage.operation_id) if self.packing_stage else None
		return [row for row in self.materials if cint(row.operation_id) != packing_id]

	@property
	def packing_materials(self):
		packing_id = cint(self.packing_stage.operation_id) if self.packing_stage else None
		return [row for row in self.materials if cint(row.operation_id) == packing_id]

	@property
	def balance_row(self):
		return next((row for row in self.raw_materials if row.is_balance_item), None)

	@property
	def output_weight(self):
		return flt(self.item.weight_per_unit)

	@cached_property
	def machines(self):
		return get_workstation_details(
			tuple(sorted({row.workstation for row in self.stages if row.workstation}))
		)

	def get_machine_warehouse(self, stage):
		return self.machines.get(stage.workstation, {}).get("warehouse")

	def is_packing_machine(self, stage):
		return self.machines.get(stage.workstation, {}).get("machine_model") in PACKING_MACHINE_MODELS

	@property
	def sequences(self):
		sequences = defaultdict(list)
		for stage in self.stages:
			sequences[cint(stage.sequence_id)].append(stage)
		return [sequences[sequence_id] for sequence_id in sorted(sequences)]

	@cached_property
	def weight_factors(self):
		items = [row.item_code for row in self.raw_materials]
		items += [row.output_item for row in self.process_stages if row.output_item]
		return get_weight_factors(items, self.item.weight_uom)

	def get_weight(self, item_code, qty):
		factor = flt(self.weight_factors.get(item_code))
		return flt(qty) / factor if factor else 0

	def to_stock_qty(self, item_code, weight):
		return flt(weight) * flt(self.weight_factors.get(item_code))

	@property
	def can_compute(self):
		return (
			self.output_weight > 0
			and bool(self.item.weight_uom)
			and len(self.stages) > 1
			and all(0 < flt(stage.yield_percentage) <= 100 for stage in self.process_stages)
			and all(flt(self.weight_factors.get(row.item_code)) for row in self.raw_materials)
		)

	def get_charged(self, balance_weight=0.0):
		charged = defaultdict(float)
		for row in self.raw_materials:
			weight = balance_weight if row.is_balance_item else self.get_weight(row.item_code, row.qty)
			charged[cint(row.operation_id)] += weight
		return charged

	def get_flows(self, charged):
		flows, carried = {}, 0.0
		for sequence in self.sequences:
			sequence = [stage for stage in sequence if stage is not self.packing_stage]
			for stage in sequence:
				weight = carried / len(sequence) + charged[cint(stage.operation_id)]
				flows[cint(stage.operation_id)] = (weight, weight * flt(stage.yield_percentage) / 100)
			if sequence:
				carried = sum(flows[cint(stage.operation_id)][1] for stage in sequence)
		return flows, carried

	@property
	def balance_weight(self):
		empty = self.get_flows(self.get_charged(0))[1]
		unit = self.get_flows(self.get_charged(1))[1] - empty
		return (self.output_weight - empty) / unit if unit > 0 else 0

	@property
	def made_weight(self):
		balance = self.balance_weight if self.balance_row else 0
		return self.get_flows(self.get_charged(balance))[1]

	def apply(self):
		self.remove_stage_inputs()
		self.set_sequence_ids()
		self.set_material_uoms()
		if not self.can_compute:
			return

		balance = self.balance_weight if self.balance_row else 0
		if self.balance_row:
			qty = self.to_stock_qty(self.balance_row.item_code, balance)
			self.balance_row.qty = flt(max(qty, 0), QTY_PRECISION)

		flows = self.get_flows(self.get_charged(balance))[0]
		for stage in self.process_stages:
			if stage.output_item:
				weight = flows[cint(stage.operation_id)][1]
				stage.output_quantity = flt(self.to_stock_qty(stage.output_item, weight), QTY_PRECISION)
		self.packing_stage.output_quantity = 1

	def remove_stage_inputs(self):
		for row in list(self.design.materials):
			if not cint(row.bom_node_id) and row.from_operation_id:
				self.design.remove(row)

	def set_sequence_ids(self):
		if not any(cint(stage.sequence_id) for stage in self.stages):
			for number, stage in enumerate(self.stages, start=1):
				stage.sequence_id = number

	def set_material_uoms(self):
		stock_uoms = dict(
			frappe.get_all(
				"Item",
				filters={"name": ("in", [row.item_code for row in self.materials if row.item_code])},
				fields=["name", "stock_uom"],
				as_list=True,
			)
		)
		for row in self.materials:
			if row.item_code:
				row.uom = stock_uoms.get(row.item_code)

	def get_stage_inputs(self):
		inputs = []
		for previous, sequence in zip(self.sequences, self.sequences[1:], strict=False):
			for stage in sequence:
				inputs.extend(
					frappe._dict(stage=stage, source=source, qty=flt(source.output_quantity) / len(sequence))
					for source in previous
				)
		return inputs

	def get_problems(self):
		return [
			*self.get_product_problems(),
			*self.get_formula_problems(),
			*self.get_stage_problems(),
		]

	def get_product_problems(self):
		problems = []
		if self.design.item_code and (self.output_weight <= 0 or not self.item.weight_uom):
			problems.append(_("Set Weight Per Unit and Weight UOM on {0}").format(self.design.item_code))
		if not self.design.raw_material_warehouse:
			problems.append(_("Set the Raw Material Warehouse"))
		return problems

	def get_formula_problems(self):
		materials = self.raw_materials
		if not materials:
			return [_("Add at least one raw material")]

		problems = []
		items = [row.item_code for row in materials]
		if duplicates := {item for item in items if item and items.count(item) > 1}:
			problems.append(
				_("Raw material {0} is in the formula more than once").format(", ".join(duplicates))
			)
		if len([row for row in materials if row.is_balance_item]) > 1:
			problems.append(_("Only one raw material can be the balance item"))
		if any(not row.is_balance_item and flt(row.qty) <= 0 for row in materials):
			problems.append(_("Every raw material needs a quantity above zero"))
		if self.can_compute:
			problems.extend(self.get_balance_problems())
		return problems + self.get_unit_problems(items)

	def get_balance_problems(self):
		batch = flt(self.design.qty) or 1
		uom = self.item.weight_uom
		if self.balance_row and self.balance_weight <= 0:
			return [
				_("The other raw materials already make the batch, so {0} has nothing to top up").format(
					self.balance_row.item_code
				)
			]
		made = self.made_weight
		if not self.balance_row and abs(made - self.output_weight) > self.output_weight * WEIGHT_TOLERANCE:
			return [
				_(
					"The formula makes {0} {1} but the batch needs {2} {1}. Change a quantity or pick a balance item."
				).format(flt(made * batch, 3), uom, flt(self.output_weight * batch, 3))
			]
		return []

	def get_unit_problems(self, item_codes):
		if not self.item.weight_uom:
			return []
		return [
			_("Add {0} to the units of measure of {1}").format(self.item.weight_uom, item_code)
			for item_code in item_codes
			if item_code and not self.weight_factors.get(item_code)
		]

	def get_stage_problems(self):
		problems = []
		if len(self.stages) < 2:
			problems.append(_("Add at least one process stage before packing"))
		if self.packing_stage and not self.is_packing_machine(self.packing_stage):
			problems.append(_("End with exactly one packing stage, a Filling Line or a Bagging Line"))
		if any(self.is_packing_machine(stage) for stage in self.process_stages):
			problems.append(_("Only the last stage can pack the finished good"))
		if self.packing_stage and not self.packing_materials:
			problems.append(_("Add at least one packing material"))

		for number, stage in enumerate(self.stages, start=1):
			problems.extend(self.get_problems_for_stage(number, stage))
		return problems + self.get_sequence_problems() + self.get_first_sequence_problems()

	def get_problems_for_stage(self, number, stage):
		problems = []
		if not stage.operation:
			problems.append(_("Stage {0} needs an Operation").format(number))
		if not stage.workstation:
			problems.append(_("Stage {0} needs a Workstation").format(number))
		elif not self.get_machine_warehouse(stage):
			problems.append(_("Set a warehouse on workstation {0}").format(stage.workstation))
		if stage is self.packing_stage:
			return problems

		if not 0 < flt(stage.yield_percentage) <= 100:
			problems.append(_("Stage {0} yield must be between 1 and 100%").format(number))
		return problems + self.get_unit_problems([stage.output_item])

	def get_sequence_problems(self):
		problems, previous = [], 0
		for number, stage in enumerate(self.stages, start=1):
			sequence_id = cint(stage.sequence_id)
			if number == 1 and sequence_id != 1:
				problems.append(_("Stage 1 needs Sequence ID 1"))
			elif number > 1 and sequence_id not in (previous, previous + 1):
				problems.append(
					_("Stage {0} needs Sequence ID {1} or {2}").format(number, previous, previous + 1)
				)
			previous = sequence_id

		if len(self.stages) > 1 and cint(self.stages[-1].sequence_id) == cint(self.stages[-2].sequence_id):
			problems.append(_("The packing stage runs on its own, after all other stages"))
		return problems

	def get_first_sequence_problems(self):
		charged = {cint(row.operation_id) for row in self.raw_materials}
		first = self.sequences[0] if self.process_stages else []
		return [
			_("Stage {0} starts the process, so give it at least one raw material").format(
				self.stages.index(stage) + 1
			)
			for stage in first
			if stage is not self.packing_stage and cint(stage.operation_id) not in charged
		]


def get_weight_factors(item_codes, weight_uom):
	item_codes = list(set(filter(None, item_codes)))
	if not item_codes or not weight_uom:
		return {}

	stock_uoms = dict(
		frappe.get_all("Item", filters={"name": ("in", item_codes)}, fields=["name", "stock_uom"], as_list=1)
	)
	item_factors = dict(
		frappe.get_all(
			"UOM Conversion Detail",
			filters={"parenttype": "Item", "parent": ("in", item_codes), "uom": weight_uom},
			fields=["parent", "conversion_factor"],
			as_list=1,
		)
	)

	factors = {}
	for item_code, stock_uom in stock_uoms.items():
		if stock_uom == weight_uom:
			factors[item_code] = 1.0
		else:
			factors[item_code] = item_factors.get(item_code) or get_uom_conv_factor(weight_uom, stock_uom)
	return factors

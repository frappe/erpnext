from functools import cached_property

import frappe
from frappe.utils import cint, flt

from erpnext.manufacturing.doctype.bom_creator.process_formula import get_weight_factors
from erpnext.manufacturing.doctype.workstation_type.workstation_type import get_workstation_details


class RunPlan:
	def __init__(self, work_order):
		self.work_order = work_order
		self.operations = work_order.operations
		fields = ["formula_tolerance", "bom_creator"]
		self.bom = frappe.get_cached_value("BOM", work_order.bom_no, fields, as_dict=True) or frappe._dict()
		fields = ["item_name", "stock_uom", "weight_per_unit", "weight_uom"]
		self.item = (
			frappe.get_cached_value("Item", work_order.production_item, fields, as_dict=True)
			or frappe._dict()
		)

	@property
	def weight_uom(self):
		return self.item.weight_uom

	@property
	def weight_per_unit(self):
		return flt(self.item.weight_per_unit)

	@property
	def tolerance(self):
		return flt(self.bom.formula_tolerance)

	@cached_property
	def machines(self):
		return get_workstation_details(
			tuple(sorted({row.workstation for row in self.operations if row.workstation}))
		)

	@cached_property
	def outputs(self):
		last = len(self.operations)
		return {
			row.finished_good: row.idx for row in self.operations if row.idx != last and row.finished_good
		}

	def get_rows(self, idx):
		return [row for row in self.work_order.required_items if cint(row.operation_row_id) == idx]

	def is_input(self, row, idx):
		return self.outputs.get(row.item_code, idx) != idx

	@cached_property
	def stages(self):
		stages = [self.get_stage(row) for row in self.operations]
		for stage in stages:
			stage.inputs = [
				self.get_input(row, stages[self.outputs[row.item_code] - 1])
				for row in self.get_rows(stage.idx)
				if self.is_input(row, stage.idx)
			]
			stage.input_weight = flt(
				sum(self.get_weight(row.item_code, row.required_qty) for row in self.get_rows(stage.idx)), 3
			)
		return stages

	def get_stage(self, operation):
		is_packing = operation.idx == len(self.operations)
		output_item = self.work_order.production_item if is_packing else operation.finished_good
		output_qty = flt(self.work_order.qty) if is_packing else flt(operation.output_qty)
		return frappe._dict(
			idx=operation.idx,
			stage_name=operation.operation,
			workstation=operation.workstation,
			warehouse=operation.wip_warehouse,
			operation=operation.operation,
			time_in_mins=flt(operation.time_in_mins),
			sequence_id=cint(operation.sequence_id) or operation.idx,
			is_packing=is_packing,
			output_item=output_item,
			output_qty=output_qty,
			output_weight=flt(
				output_qty * self.weight_per_unit if is_packing else self.get_weight(output_item, output_qty),
				3,
			),
		)

	@staticmethod
	def get_input(row, source):
		return frappe._dict(
			stage_idx=source.idx,
			item_code=row.item_code,
			warehouse=row.source_warehouse,
			share=flt(row.required_qty) / flt(source.output_qty) if flt(source.output_qty) else 0,
			qty=flt(row.required_qty),
		)

	@cached_property
	def weight_factors(self):
		items = [row.item_code for row in self.work_order.required_items]
		return get_weight_factors([*items, *self.outputs], self.weight_uom)

	def get_weight(self, item_code, qty):
		factor = flt(self.weight_factors.get(item_code))
		return flt(qty) / factor if factor else 0

	@property
	def packing_idx(self):
		return len(self.operations)

	@property
	def raw_rows(self):
		return [
			row
			for row in self.work_order.required_items
			if cint(row.operation_row_id) != self.packing_idx
			and not self.is_input(row, cint(row.operation_row_id))
		]

	@property
	def packing_rows(self):
		return [row for row in self.get_rows(self.packing_idx) if not self.is_input(row, self.packing_idx)]

	@property
	def warehouses(self):
		return {row.source_warehouse for row in [*self.raw_rows, *self.packing_rows] if row.source_warehouse}

	@cached_property
	def balance_items(self):
		return set(
			frappe.get_all(
				"BOM Item",
				filters={"parent": self.work_order.bom_no, "parenttype": "BOM", "is_balance_item": 1},
				pluck="item_code",
			)
		)

	@cached_property
	def storage(self):
		if not self.bom.bom_creator:
			return {}
		return dict(
			frappe.get_all(
				"BOM Creator Material",
				filters={"parent": self.bom.bom_creator},
				fields=["item_code", "storage"],
				as_list=True,
			)
		)

	@property
	def input_weight(self):
		return sum(self.get_weight(row.item_code, row.required_qty) for row in self.raw_rows)

	@property
	def output_weight(self):
		return flt(self.work_order.qty) * self.weight_per_unit

	def get_materials(self):
		total = self.input_weight
		materials = []
		for row in self.raw_rows:
			weight = self.get_weight(row.item_code, row.required_qty)
			materials.append(
				frappe._dict(
					item_code=row.item_code,
					item_name=row.item_name,
					storage=self.storage.get(row.item_code) or "Tank",
					stage_row_id=cint(row.operation_row_id),
					is_balance_item=int(row.item_code in self.balance_items),
					percentage=flt(weight / total * 100, 3) if total else 0,
					weight=flt(weight, 3),
					qty=flt(row.required_qty),
					source_warehouse=row.source_warehouse,
				)
			)
		return materials

	def get_packing_materials(self):
		qty = flt(self.work_order.qty) or 1
		return [
			frappe._dict(
				item_code=row.item_code,
				item_name=row.item_name,
				qty=flt(row.required_qty),
				qty_per_unit=flt(row.required_qty) / qty,
				source_warehouse=row.source_warehouse,
			)
			for row in self.packing_rows
		]

	def as_dict(self):
		return frappe._dict(
			qty=flt(self.work_order.qty),
			stock_uom=self.work_order.stock_uom,
			weight_uom=self.weight_uom,
			weight_per_unit=self.weight_per_unit,
			process_yield=flt(self.output_weight / self.input_weight * 100, 3) if self.input_weight else 0,
			output_weight=flt(self.output_weight, 3),
			input_weight=flt(self.input_weight, 3),
			materials=self.get_materials(),
			stages=self.stages,
			packing_materials=self.get_packing_materials(),
		)

	def get_plant_doc(self):
		return frappe._dict(
			name=self.work_order.name,
			production_item=self.work_order.production_item,
			stages=[self.get_plant_stage(stage) for stage in self.stages],
			materials=self.get_materials(),
			packing_materials=self.get_packing_materials(),
		)

	def get_plant_stage(self, stage):
		machine = self.machines.get(stage.workstation, {})
		yield_percentage = stage.output_weight / stage.input_weight * 100 if stage.input_weight else 100
		return frappe._dict(
			stage_name=stage.stage_name,
			workstation=stage.workstation,
			workstation_type=machine.get("workstation_type"),
			machine_model=machine.get("machine_model"),
			semi_finished_good=None if stage.is_packing else stage.output_item,
			sequence_id=stage.sequence_id,
			yield_percentage=flt(min(yield_percentage, 100), 3),
		)

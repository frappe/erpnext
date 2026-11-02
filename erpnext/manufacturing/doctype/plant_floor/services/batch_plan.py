from collections import defaultdict

import frappe
from frappe.utils import cint, flt

from erpnext.stock.doctype.item.item import get_uom_conv_factor


class BatchPlan:
	def __init__(self, plant_floor, qty=None):
		self.plant_floor = plant_floor
		self.qty = flt(qty if qty is not None else plant_floor.batch_size)
		self.item = (
			frappe.get_cached_value(
				"Item",
				plant_floor.production_item,
				["item_name", "stock_uom", "weight_per_unit", "weight_uom"],
				as_dict=True,
			)
			or frappe._dict()
		)

	@property
	def weight_uom(self):
		return self.item.weight_uom

	@property
	def weight_per_unit(self):
		return flt(self.item.weight_per_unit)

	@property
	def process_stages(self):
		return [stage for stage in self.plant_floor.stages if not self.plant_floor.is_packing_stage(stage)]

	@property
	def process_yield(self):
		return self.get_flows(1)[1]

	@property
	def output_weight(self):
		return self.qty * self.weight_per_unit

	@property
	def input_weight(self):
		return self.output_weight / self.process_yield if self.process_yield else 0

	@property
	def balance_percentage(self):
		return 100 - sum(flt(row.percentage) for row in self.plant_floor.materials if not row.is_balance_item)

	@property
	def weight_factors(self):
		if not hasattr(self, "_weight_factors"):
			items = [row.item_code for row in self.plant_floor.materials]
			items += [stage.semi_finished_good for stage in self.process_stages if stage.semi_finished_good]
			self._weight_factors = get_weight_factors(items, self.weight_uom)
		return self._weight_factors

	def get_percentage(self, row):
		return self.balance_percentage if row.is_balance_item else flt(row.percentage)

	def to_stock_qty(self, item_code, weight):
		return flt(weight * flt(self.weight_factors.get(item_code)), 3)

	def get_materials(self):
		materials = []
		for row in self.plant_floor.materials:
			weight = self.input_weight * self.get_percentage(row) / 100
			materials.append(
				frappe._dict(
					item_code=row.item_code,
					item_name=row.item_name,
					storage=row.storage,
					stage_row_id=get_stage_row_id(row),
					is_balance_item=row.is_balance_item,
					percentage=self.get_percentage(row),
					weight=flt(weight, 3),
					qty=self.to_stock_qty(row.item_code, weight),
				)
			)
		return materials

	def get_flows(self, input_weight):
		charged = defaultdict(float)
		for row in self.plant_floor.materials:
			charged[get_stage_row_id(row)] += input_weight * self.get_percentage(row) / 100

		flows, carried = {}, 0.0
		for sequence in self.plant_floor.stage_sequences:
			for stage in sequence:
				weight = carried / len(sequence) + charged[stage.idx]
				flows[stage.idx] = (weight, weight * self.get_yield(stage))
			carried = sum(flows[stage.idx][1] for stage in sequence)
		return flows, carried

	def get_yield(self, stage):
		return 1 if self.plant_floor.is_packing_stage(stage) else flt(stage.yield_percentage) / 100

	def get_stages(self):
		flows, stages, previous = self.get_flows(self.input_weight)[0], {}, []
		for sequence_id, sequence in enumerate(self.plant_floor.stage_sequences, start=1):
			for stage in sequence:
				stages[stage.idx] = self.get_stage(stage, sequence_id, flows[stage.idx])
				stages[stage.idx].inputs = get_inputs(previous, len(sequence))
			previous = [stages[stage.idx] for stage in sequence]
		return [stages[stage.idx] for stage in self.plant_floor.stages]

	def get_stage(self, stage, sequence_id, flow):
		is_packing = self.plant_floor.is_packing_stage(stage)
		output_item = self.plant_floor.production_item if is_packing else stage.semi_finished_good
		return frappe._dict(
			idx=stage.idx,
			stage_name=stage.stage_name,
			workstation=stage.workstation,
			warehouse=self.plant_floor.machine_warehouses.get(stage.workstation),
			operation=stage.operation,
			time_in_mins=flt(stage.time_in_mins),
			sequence_id=sequence_id,
			is_packing=is_packing,
			input_weight=flt(flow[0], 3),
			output_weight=flt(flow[1], 3),
			output_item=output_item,
			output_qty=self.qty if is_packing else self.to_stock_qty(output_item, flow[1]),
		)

	def get_packing_materials(self):
		return [
			frappe._dict(
				item_code=row.item_code, item_name=row.item_name, qty=flt(self.qty * flt(row.qty_per_unit), 3)
			)
			for row in self.plant_floor.packing_materials
		]

	def as_dict(self):
		return frappe._dict(
			qty=self.qty,
			stock_uom=self.item.stock_uom,
			weight_uom=self.weight_uom,
			weight_per_unit=self.weight_per_unit,
			process_yield=flt(self.process_yield * 100, 3),
			output_weight=flt(self.output_weight, 3),
			input_weight=flt(self.input_weight, 3),
			materials=self.get_materials(),
			stages=self.get_stages(),
			packing_materials=self.get_packing_materials(),
		)


def get_stage_row_id(row):
	return cint(row.stage_row_id) or 1


def get_inputs(sources, share_count):
	return [
		frappe._dict(
			stage_idx=source.idx,
			item_code=source.output_item,
			share=1 / share_count,
			qty=flt(source.output_qty / share_count, 3),
		)
		for source in sources
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

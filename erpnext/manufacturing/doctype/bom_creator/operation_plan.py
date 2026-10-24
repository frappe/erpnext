# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.utils import cint, flt

from erpnext.manufacturing.doctype.bom_creator.bom_plan import BOMPlan


class OperationPlan(BOMPlan):
	def __init__(self, design):
		super().__init__(design)
		self.operations = defaultdict(list)
		self.materials = defaultdict(list)
		for row in design.operations:
			self.operations[cint(row.bom_node_id)].append(row)

		for row in design.materials:
			self.materials[cint(row.bom_node_id)].append(row)

	@property
	def bom_node_ids(self) -> list[int]:
		return sorted({0, *self.operations, *self.materials})

	def get_bom_node_ids(self) -> list[int]:
		return self.bom_node_ids

	@property
	def produces_item_at_each_operation(self) -> bool:
		return bool(self.design.track_semi_finished_goods)

	def validate(self):
		self.set_operation_ids()
		for row in self.design.operations:
			self.validate_operation(row)

		for row in self.design.materials:
			self.validate_material(row)

	def set_operation_ids(self):
		last_id = max((cint(row.operation_id) for row in self.design.operations), default=0)
		for row in self.design.operations:
			if not row.operation_id:
				last_id += 1
				row.operation_id = last_id

	def validate_operation(self, row):
		self.validate_node(row.bom_node_id, _("Operations row #{0}").format(row.idx))
		self.validate_node(row.output_node_id, _("Operations row #{0}").format(row.idx))

	def validate_material(self, row):
		label = _("Materials row #{0}").format(row.idx)
		sources = [row.part_node_id, row.item_code, row.from_operation_id]
		if len([source for source in sources if source]) != 1:
			frappe.throw(
				_("{0}: choose one design part, one item or one earlier operation output.").format(label)
			)

		self.validate_node(row.bom_node_id, label)
		self.validate_node(row.part_node_id, label)
		operation_ids = [cint(operation.operation_id) for operation in self.operations[cint(row.bom_node_id)]]
		if row.operation_id and cint(row.operation_id) not in operation_ids:
			frappe.throw(_("{0}: the operation is not part of this BOM.").format(label))

		if row.from_operation_id:
			self.validate_previous_output(row, operation_ids, label)

	def validate_previous_output(self, row, operation_ids: list[int], label: str):
		if not self.produces_item_at_each_operation:
			frappe.throw(
				_("{0}: an operation output can be used only when each operation produces an item.").format(
					label
				)
			)

		if cint(row.from_operation_id) not in operation_ids or not row.operation_id:
			frappe.throw(_("{0}: choose an earlier operation of this BOM.").format(label))

		if operation_ids.index(cint(row.from_operation_id)) >= operation_ids.index(cint(row.operation_id)):
			frappe.throw(
				_("{0}: an operation can use only the output of an earlier operation.").format(label)
			)

	def validate_node(self, node_id, label: str):
		if cint(node_id) and cint(node_id) not in self.parts:
			frappe.throw(_("{0}: design part node {1} does not exist.").format(label, node_id))

	def get_output_item(self, row, is_last: bool) -> str | None:
		if is_last:
			return self.get_node_item(row.bom_node_id)

		return self.get_node_item(row.output_node_id) if row.output_node_id else row.output_item

	def get_material_item(self, row) -> str | None:
		if row.part_node_id:
			return self.get_node_item(row.part_node_id)

		if row.from_operation_id:
			operations = self.operations[cint(row.bom_node_id)]
			source = next(op for op in operations if cint(op.operation_id) == cint(row.from_operation_id))
			return self.get_output_item(source, source is operations[-1])

		return row.item_code

	def get_bom_name(self, node_id: int) -> str:
		if not node_id:
			return self.design.design_name

		return self.parts[node_id].part_name or self.parts[node_id].part_number

	def get_problems(self) -> list[str]:
		problems = []
		for node_id in self.bom_node_ids:
			problems.extend(self.get_bom_problems(node_id))

		return problems

	def get_bom_problems(self, node_id: int) -> list[str]:
		name = bold(self.get_bom_name(node_id))
		operations = self.operations[node_id]
		problems = []
		if not self.get_node_item(node_id):
			problems.append(_("{0}: map an item before creating its BOM.").format(name))

		if not self.materials[node_id] and not operations:
			problems.append(_("{0}: add raw materials or operations.").format(name))

		for index, row in enumerate(operations, start=1):
			problems.extend(self.get_operation_problems(name, index, row, row is operations[-1]))

		for row in self.materials[node_id]:
			if not self.get_material_item(row):
				problems.append(_("{0}: map an item for every raw material.").format(name))
				break

		return problems

	def get_operation_problems(self, name: str, index: int, row, is_last: bool) -> list[str]:
		step = _("{0} step {1} ({2})").format(name, index, row.operation)
		problems = []
		if not row.workstation_type:
			problems.append(_("{0}: set the Workstation Type.").format(step))

		if flt(row.time_in_mins) <= 0:
			problems.append(_("{0}: set the operation time.").format(step))

		if self.produces_item_at_each_operation and not is_last and not self.get_output_item(row, is_last):
			problems.append(_("{0}: choose the item this step makes.").format(step))

		return problems

	def get_bom_order(self) -> list[int]:
		node_by_item = {self.get_node_item(node_id): node_id for node_id in self.bom_node_ids}
		order, visiting = [], set()

		def visit(node_id: int):
			if node_id in order:
				return

			if node_id in visiting:
				frappe.throw(
					_("BOM {0} uses itself as a raw material.").format(bold(self.get_bom_name(node_id)))
				)

			visiting.add(node_id)
			for item_code in self.get_items_used(node_id):
				if node_by_item.get(item_code, node_id) != node_id:
					visit(node_by_item[item_code])

			visiting.discard(node_id)
			order.append(node_id)

		for node_id in self.bom_node_ids:
			visit(node_id)

		return order

	def get_items_used(self, node_id: int) -> set[str]:
		items = {self.get_material_item(row) for row in self.materials[node_id]}
		if self.produces_item_at_each_operation:
			items.update(self.get_output_item(row, False) for row in self.operations[node_id][:-1])

		return items

	def make_bom(self, node_id: int, boms: dict[str, str]) -> str:
		operations = self.operations[node_id]
		quantity = self.get_bom_quantity(node_id)
		bom = self.new_bom(node_id)
		bom.update(
			{
				"with_operations": 1 if operations else 0,
				"track_semi_finished_goods": 1 if operations and self.produces_item_at_each_operation else 0,
			}
		)

		for row in operations:
			bom.append("operations", self.get_bom_operation(row, row is operations[-1], boms, quantity))

		stock_uoms = self.get_stock_uoms(node_id)
		for row in self.materials[node_id]:
			bom.append("items", self.get_material_bom_item(row, operations, boms, stock_uoms, quantity))

		return self.submit_bom(bom)

	def get_bom_operation(self, row, is_last: bool, boms: dict[str, str], quantity: float) -> dict:
		operation = {
			"operation": row.operation,
			"workstation_type": row.workstation_type,
			"time_in_mins": row.time_in_mins,
		}
		if self.produces_item_at_each_operation:
			output_item = self.get_output_item(row, is_last)
			operation.update(
				{
					"finished_good": output_item,
					"finished_good_qty": (flt(row.output_quantity) or 1) * quantity,
					"is_final_finished_good": 1 if is_last else 0,
					"bom_no": "" if is_last else boms.get(output_item, ""),
				}
			)

		return operation

	def get_material_bom_item(
		self, row, operations: list, boms: dict[str, str], stock_uoms: dict, quantity: float
	) -> dict:
		item_code = self.get_material_item(row)
		part = self.parts.get(cint(row.part_node_id))
		uom = row.uom or stock_uoms.get(item_code)
		bom_item = self.get_bom_item(item_code, flt(row.qty) * quantity, uom, boms, part)
		if row.from_operation_id:
			bom_item.update({"do_not_explode": 1, "bom_no": ""})
		operation_ids = [cint(operation.operation_id) for operation in operations]
		if row.operation_id and self.produces_item_at_each_operation:
			bom_item["operation_row_id"] = operation_ids.index(cint(row.operation_id)) + 1
		elif row.operation_id:
			bom_item["operation"] = operations[operation_ids.index(cint(row.operation_id))].operation

		return bom_item

	def get_stock_uoms(self, node_id: int) -> dict[str, str]:
		item_codes = list({self.get_material_item(row) for row in self.materials[node_id]})
		items = frappe.get_all("Item", filters={"name": ("in", item_codes)}, fields=["name", "stock_uom"])
		return {item.name: item.stock_uom for item in items}

	def get_used_node_ids(self) -> set[int]:
		node_ids = {cint(row.part_node_id) for row in self.design.materials}
		node_ids.update(cint(row.output_node_id) for row in self.design.operations)
		node_ids.update(self.bom_node_ids)
		return node_ids - {0}

	def remap_nodes(self, new_node_ids: dict[int, int]):
		for row in list(self.design.operations):
			self.remap_row(row, ("bom_node_id", "output_node_id"), new_node_ids, "operations")

		for row in list(self.design.materials):
			self.remap_row(row, ("bom_node_id", "part_node_id"), new_node_ids, "materials")

		operation_ids = {cint(row.operation_id) for row in self.design.operations}
		for row in list(self.design.materials):
			if cint(row.from_operation_id) and cint(row.from_operation_id) not in operation_ids:
				self.design.remove(row)
			elif cint(row.operation_id) not in operation_ids:
				row.operation_id = 0

		for table in ("operations", "materials"):
			for index, row in enumerate(self.design.get(table), start=1):
				row.idx = index

	def remap_row(self, row, fields: tuple, new_node_ids: dict[int, int], table: str):
		for field in fields:
			if not cint(row.get(field)):
				continue

			if cint(row.get(field)) not in new_node_ids:
				self.design.remove(row)
				frappe.msgprint(
					_(
						"A row in {0} was removed because its design part is not in the new design file."
					).format(_(table.title()))
				)
				return

			row.set(field, new_node_ids[cint(row.get(field))])

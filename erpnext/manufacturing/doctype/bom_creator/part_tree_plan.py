# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom_creator.bom_plan import BOMPlan


class PartTreePlan(BOMPlan):
	def __init__(self, design):
		super().__init__(design)
		self.children = defaultdict(list)
		for row in design.items:
			if not row.exclude_from_bom:
				self.children[row.parent_node_id or 0].append(row)

	def get_used_node_ids(self) -> set[int]:
		node_ids, pending = set(), [0]
		while pending:
			for row in self.children[pending.pop()]:
				node_ids.add(row.node_id)
				pending.append(row.node_id)

		return node_ids

	def get_bom_node_ids(self) -> list[int]:
		return [0, *(node_id for node_id in self.get_used_node_ids() if self.children[node_id])]

	def get_problems(self) -> list[str]:
		problems = []
		if not self.design.item_code:
			problems.append(_("Map the finished good to an item."))

		if not self.children[0]:
			problems.append(_("Add raw materials to the finished good."))

		used = self.get_used_node_ids()
		unmapped = [
			row.part_name or row.part_number
			for row in self.design.items
			if row.node_id in used and not row.item_code
		]
		if unmapped:
			problems.append(_("Map an item to these parts: {0}").format(", ".join(unmapped)))

		problems.extend(self.get_duplicate_problems())
		problems.extend(self.get_assembly_problems(used))
		problems.extend(self.get_cycle_problems(used))
		return problems

	def get_duplicate_problems(self) -> list[str]:
		problems = []
		for siblings in self.children.values():
			seen = {}
			for row in siblings:
				if not row.item_code:
					continue

				other = seen.setdefault(row.item_code, row)
				if other is not row and (self.children[row.node_id] or self.children[other.node_id]):
					problems.append(
						_("Parts {0} and {1} in the same assembly are mapped to item {2}.").format(
							bold(other.part_name), bold(row.part_name), bold(row.item_code)
						)
					)

		return problems

	def get_assembly_problems(self, used: set[int]) -> list[str]:
		problems, assemblies = [], {}
		for row in self.design.items:
			if row.node_id not in used or not row.item_code or not self.children[row.node_id]:
				continue

			materials = sorted(
				(part.item_code or "", part.uom or "", flt(qty)) for part, qty in self.merge_rows(row.node_id)
			)
			other, other_materials = assemblies.setdefault(row.item_code, (row, materials))
			if other is not row and other_materials != materials:
				problems.append(
					_(
						"Assemblies {0} and {1} are mapped to item {2} but have different raw materials."
					).format(
						bold(other.part_name or other.part_number),
						bold(row.part_name or row.part_number),
						bold(row.item_code),
					)
				)

		return problems

	def get_cycle_problems(self, used: set[int]) -> list[str]:
		problems = []
		for row in self.design.items:
			if row.node_id not in used or not row.item_code:
				continue

			parent = self.parts.get(row.parent_node_id)
			ancestor_items = {self.design.item_code}
			while parent:
				ancestor_items.add(parent.item_code)
				parent = self.parts.get(parent.parent_node_id)

			if row.item_code in ancestor_items:
				problems.append(
					_("Part {0} is mapped to item {1}, which is also its own assembly.").format(
						bold(row.part_name or row.part_number), bold(row.item_code)
					)
				)

		return problems

	def get_bom_order(self) -> list[int]:
		order = []

		def visit(node_id: int):
			for row in self.children[node_id]:
				if self.children[row.node_id]:
					visit(row.node_id)

			order.append(node_id)

		visit(0)
		return order

	def make_bom(self, node_id: int, boms: dict[str, str]) -> str:
		bom = self.new_bom(node_id)
		quantity = self.get_bom_quantity(node_id)
		if not node_id:
			self.set_routing(bom)

		for part, qty in self.merge_rows(node_id):
			bom_item = self.get_bom_item(part.item_code, qty * quantity, part.uom, boms, part)
			bom_item["operation"] = part.operation if bom.with_operations else None
			bom.append("items", bom_item)

		return self.submit_bom(bom)

	def set_routing(self, bom):
		if self.design.is_phantom:
			return

		if self.design.routing or any(row.operation for row in self.design.items):
			bom.update({"routing": self.design.routing, "with_operations": 1})
			bom.transfer_material_against = "Work Order"

	def merge_rows(self, node_id: int) -> list[tuple]:
		merged = {}
		for row in self.children[node_id]:
			key = (row.item_code, row.uom)
			part, qty = merged.get(key, (row, 0))
			merged[key] = (part, qty + flt(row.qty))

		return list(merged.values())

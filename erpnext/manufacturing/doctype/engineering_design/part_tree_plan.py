# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.utils import flt


class PartTreePlan:
	def __init__(self, design):
		self.design = design
		self.children = defaultdict(list)
		for row in design.parts:
			if not row.exclude_from_bom:
				self.children[row.parent_node_id or 0].append(row)

	def get_used_node_ids(self) -> set[int]:
		node_ids, pending = set(), [0]
		while pending:
			for row in self.children[pending.pop()]:
				node_ids.add(row.node_id)
				pending.append(row.node_id)

		return node_ids

	def get_problems(self) -> list[str]:
		problems = []
		if not self.design.item_code:
			problems.append(_("Map the finished good to an item."))

		if not self.children[0]:
			problems.append(_("Add raw materials to the finished good."))

		used = self.get_used_node_ids()
		unmapped = [
			row.part_name or row.part_number
			for row in self.design.parts
			if row.node_id in used and not row.item_code
		]
		if unmapped:
			problems.append(_("Map an item to these parts: {0}").format(", ".join(unmapped)))

		problems.extend(self.get_duplicate_problems())
		return problems

	def get_duplicate_problems(self) -> list[str]:
		problems = []
		for siblings in self.children.values():
			seen = {}
			for row in siblings:
				other = seen.setdefault(row.item_code, row)
				if other is not row and (self.children[row.node_id] or self.children[other.node_id]):
					problems.append(
						_("Parts {0} and {1} in the same assembly are mapped to item {2}.").format(
							bold(other.part_name), bold(row.part_name), bold(row.item_code)
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

	def get_node_item(self, node_id: int) -> str:
		if not node_id:
			return self.design.item_code

		return next(row.item_code for row in self.design.parts if row.node_id == node_id)

	def get_bom_quantity(self, node_id: int) -> float:
		return 1 if node_id else flt(self.design.quantity) or 1

	def make_boms(self) -> dict[str, str]:
		problems = self.get_problems()
		if problems:
			frappe.throw(problems, title=_("Fix These Before Creating BOMs"), as_list=True)

		boms = {}
		for node_id in self.get_bom_order():
			item_code = self.get_node_item(node_id)
			if item_code not in boms:
				quantity = self.get_bom_quantity(node_id)
				boms[item_code] = self.make_bom(item_code, self.children[node_id], boms, quantity)

		return boms

	def make_bom(self, item_code: str, rows: list, boms: dict[str, str], quantity: float) -> str:
		bom = frappe.new_doc("BOM")
		bom.update(
			{
				"item": item_code,
				"company": self.design.company,
				"quantity": quantity,
				"rm_cost_as_per": "Valuation Rate",
			}
		)

		rows = self.merge_rows(rows)
		stock_uoms = dict(
			frappe.get_all(
				"Item",
				filters={"name": ("in", [row.item_code for row in rows])},
				fields=["name", "stock_uom"],
				as_list=True,
			)
		)
		for row in rows:
			bom.append(
				"items",
				{
					"item_code": row.item_code,
					"qty": row.quantity * quantity,
					"uom": row.uom or stock_uoms.get(row.item_code),
					"bom_no": boms.get(row.item_code, ""),
				},
			)

		bom.insert()
		bom.submit()
		return bom.name

	def merge_rows(self, rows: list) -> list:
		merged = {}
		for row in rows:
			if row.item_code in merged:
				merged[row.item_code].quantity += flt(row.quantity)
			else:
				merged[row.item_code] = frappe._dict(
					item_code=row.item_code, quantity=flt(row.quantity), uom=row.uom
				)

		return list(merged.values())

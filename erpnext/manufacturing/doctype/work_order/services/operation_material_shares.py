# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import defaultdict

import frappe
from frappe.utils import flt
from frappe.utils.caching import request_cache


class OperationMaterialShares:
	"""Splits required items between operation rows of a multi-level Work Order that share an
	operation name, by tracing each material to the BOM whose operation consumes it."""

	def __init__(self, work_order):
		self.work_order = work_order

	def get_shares(self, operation_id: str) -> dict[tuple[str, str], float]:
		"""Fraction of each (item_code, operation) required item that the operation row consumes."""
		row = next((op for op in self.work_order.operations if op.name == operation_id), None)
		if not row or not self.work_order.use_multi_level_bom:
			return {}

		boms = {op.bom for op in self.work_order.operations if op.operation == row.operation}
		if len(boms) < 2:
			return {}

		qty_by_bom = defaultdict(dict)
		for (item_code, operation, bom), qty in get_material_qty_by_owner(self.work_order.bom_no).items():
			if qty and operation == row.operation and bom in boms:
				qty_by_bom[(item_code, operation)][bom] = qty

		return {key: flt(qty.get(row.bom)) / sum(qty.values()) for key, qty in qty_by_bom.items()}


@request_cache
def get_material_qty_by_owner(bom_no: str) -> dict[tuple[str, str, str], float]:
	"""Qty per unit of `bom_no`, keyed by (item_code, operation, BOM whose operation consumes it)."""
	return BOMMaterialOwners(bom_no).get_material_qty(bom_no)


class BOMMaterialOwners:
	"""Traces the materials of a BOM tree to the BOM whose operation consumes them."""

	def __init__(self, bom_no: str):
		self.load_bom_tree(bom_no)

	def load_bom_tree(self, bom_no: str):
		self.items_by_bom, pending = {}, {bom_no}
		while pending:
			items = frappe.get_all(
				"BOM Item",
				filters={"parent": ["in", list(pending)], "parenttype": "BOM"},
				fields=["parent", "item_code", "bom_no", "operation", "stock_qty"],
			)
			self.items_by_bom.update({bom: [] for bom in pending})
			for item in items:
				self.items_by_bom[item.parent].append(item)
			pending = {item.bom_no for item in items if item.bom_no} - self.items_by_bom.keys()

		self.bom_quantity = dict(
			frappe.get_all(
				"BOM",
				filters={"name": ["in", list(self.items_by_bom)]},
				fields=["name", "quantity"],
				as_list=True,
			)
		)

	def get_material_qty(self, bom_no: str) -> defaultdict:
		"""Qty per unit of `bom_no`, keyed by (item_code, operation, BOM whose operation consumes it).

		A sub-assembly material without its own operation inherits the parent line's operation and
		belongs to the parent BOM, as in BOM explosion."""
		material_qty = defaultdict(float)
		for item in self.items_by_bom[bom_no]:
			qty = flt(item.stock_qty) / flt(self.bom_quantity[bom_no])
			if not item.bom_no:
				material_qty[(item.item_code, item.operation, bom_no)] += qty
				continue

			for (item_code, operation, bom), child_qty in self.get_material_qty(item.bom_no).items():
				key = (item_code, operation, bom) if operation else (item_code, item.operation, bom_no)
				material_qty[key] += qty * child_qty

		return material_qty

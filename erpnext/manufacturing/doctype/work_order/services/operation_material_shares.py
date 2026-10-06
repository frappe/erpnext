# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import defaultdict

import frappe
from frappe.utils import cint, flt
from frappe.utils.caching import request_cache


class OperationMaterialShares:
	"""Splits required items between Work Order operation rows that share an operation name, by
	tracing each material to the BOM operation row that consumes it."""

	def __init__(self, work_order):
		self.work_order = work_order

	def get_shares(self, operation_id: str) -> dict[tuple[str, str], float]:
		"""Fraction of each (item_code, operation) required item that the operation row consumes."""
		row = next((op for op in self.work_order.operations if op.name == operation_id), None)
		if not row or self.work_order.track_semi_finished_goods:
			return {}

		owners = self.get_operation_row_owners(row.operation)
		if len(owners) < 2:
			return {}

		present = set(owners.values()) | {(bom, 0) for bom, _row in owners.values()}
		consumed_by_row = {owners[row.name], (row.bom, 0)}
		material_qty = get_material_qty_by_owner(self.work_order.bom_no)
		unedited = self.get_unedited_required_items(material_qty)
		qty_by_owner = defaultdict(dict)
		for (item_code, operation, owner), qty in material_qty.items():
			if qty and operation == row.operation and owner in present and (item_code, operation) in unedited:
				qty_by_owner[(item_code, operation)][owner] = qty

		return {
			key: sum(qty.get(owner, 0) for owner in consumed_by_row) / sum(qty.values())
			for key, qty in qty_by_owner.items()
		}

	def get_operation_row_owners(self, operation: str) -> dict[str, tuple[str, int]]:
		"""(BOM, BOM operation row) of each Work Order row of `operation`, from the row's position
		among the rows of its BOM. Row 0 when that position no longer holds the operation, as for
		rows added on the Work Order."""
		bom_operations = get_bom_operations(
			tuple(sorted({op.bom for op in self.work_order.operations if op.bom}))
		)
		position, owners = defaultdict(int), {}
		for op in self.work_order.operations:
			operations = bom_operations.get(op.bom)
			bom_row = position[op.bom] % len(operations) + 1 if operations else 0
			position[op.bom] += 1
			if op.operation == operation:
				owners[op.name] = (
					op.bom,
					bom_row if operations and operations[bom_row - 1] == operation else 0,
				)

		return owners

	def get_unedited_required_items(self, material_qty: dict) -> set[tuple[str, str]]:
		"""(item_code, operation) keys whose Work Order requirement still equals the BOM's, so an
		item replaced or resized on the Work Order keeps matching on the operation name."""
		bom_qty = defaultdict(float)
		for (item_code, operation, _owner), qty in material_qty.items():
			bom_qty[(item_code, operation)] += qty * flt(self.work_order.qty)

		required_qty = defaultdict(float)
		for item in self.work_order.required_items:
			required_qty[(item.item_code, item.operation)] += flt(item.required_qty)

		tolerance = 10 ** -frappe.get_precision("Work Order Item", "required_qty")
		return {key for key, qty in required_qty.items() if abs(qty - bom_qty[key]) <= tolerance}


@request_cache
def get_bom_operations(bom_nos: tuple[str, ...]) -> dict[str, list[str]]:
	"""Operation names of each BOM, in row order."""
	bom_operations = defaultdict(list)
	for row in frappe.get_all(
		"BOM Operation",
		filters={"parent": ["in", bom_nos], "parenttype": "BOM"},
		fields=["parent", "operation"],
		order_by="idx",
	):
		bom_operations[row.parent].append(row.operation)

	return bom_operations


@request_cache
def get_material_qty_by_owner(bom_no: str) -> dict[tuple[str, str, tuple[str, int]], float]:
	"""Qty per unit of `bom_no`, keyed by (item_code, operation, (BOM, operation row) that consumes it)."""
	return BOMMaterialOwners(bom_no).get_material_qty(bom_no)


class BOMMaterialOwners:
	"""Traces the materials of a BOM tree to the BOM operation row that consumes them."""

	def __init__(self, bom_no: str):
		self.load_bom_tree(bom_no)

	def load_bom_tree(self, bom_no: str):
		self.items_by_bom, pending = {}, {bom_no}
		while pending:
			items = frappe.get_all(
				"BOM Item",
				filters={"parent": ["in", list(pending)], "parenttype": "BOM"},
				fields=["parent", "item_code", "bom_no", "operation", "operation_row_id", "stock_qty"],
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
		"""Qty per unit of `bom_no`, keyed by (item_code, operation, (BOM, operation row) that
		consumes it). Row 0 is a line without an Operation Row No.

		A sub-assembly material without its own operation inherits the parent line's operation and
		belongs to the parent line, as in BOM explosion."""
		material_qty = defaultdict(float)
		for item in self.items_by_bom[bom_no]:
			qty = flt(item.stock_qty) / flt(self.bom_quantity[bom_no])
			owner = (bom_no, cint(item.operation_row_id))
			if not item.bom_no:
				material_qty[(item.item_code, item.operation, owner)] += qty
				continue

			for (item_code, operation, child_owner), child_qty in self.get_material_qty(item.bom_no).items():
				key = (item_code, operation, child_owner) if operation else (item_code, item.operation, owner)
				material_qty[key] += qty * child_qty

		return material_qty

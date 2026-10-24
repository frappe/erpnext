# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom_creator.bom_csv_file import read_bom_csv_file
from erpnext.manufacturing.doctype.bom_creator.material_cost import MaterialCost
from erpnext.manufacturing.doctype.bom_creator.operation_plan import OperationPlan
from erpnext.manufacturing.doctype.bom_creator.part_tree_plan import PartTreePlan
from erpnext.manufacturing.doctype.bom_creator.step_file import read_step_file

DESIGN_FILE_READERS = {"step": read_step_file, "stp": read_step_file, "csv": read_bom_csv_file}
PART_MODEL_FORMATS = ("step", "stp", "stl", "glb")
MAPPING_FIELDS = (
	"item_code",
	"item_name",
	"uom",
	"exclude_from_bom",
	"do_not_explode",
	"bom_no",
	"is_phantom_item",
	"sourced_by_supplier",
	"operation",
	"instruction",
)


class BOMCreator(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.bom_creator_item.bom_creator_item import BOMCreatorItem
		from erpnext.manufacturing.doctype.bom_creator_material.bom_creator_material import BOMCreatorMaterial
		from erpnext.manufacturing.doctype.bom_creator_operation.bom_creator_operation import (
			BOMCreatorOperation,
		)

		amended_from: DF.Link | None
		buying_price_list: DF.Link | None
		company: DF.Link
		conversion_rate: DF.Float
		currency: DF.Link
		default_warehouse: DF.Link | None
		design_file: DF.Attach | None
		design_name: DF.Data | None
		error_log: DF.Text | None
		is_phantom: DF.Check
		item_code: DF.Link | None
		item_group: DF.Link | None
		item_name: DF.Data | None
		items: DF.Table[BOMCreatorItem]
		materials: DF.Table[BOMCreatorMaterial]
		naming_series: DF.Literal["BOM-CRE-.YYYY.-"]
		operations: DF.Table[BOMCreatorOperation]
		part_number: DF.Data | None
		plc_conversion_rate: DF.Float
		previous_revision: DF.Link | None
		price_list_currency: DF.Link | None
		project: DF.Link | None
		qty: DF.Float
		raw_material_cost: DF.Currency
		remarks: DF.TextEditor | None
		revision: DF.Int
		rm_cost_as_per: DF.Literal["Valuation Rate", "Last Purchase Rate", "Price List"]
		routing: DF.Link | None
		set_rate_based_on_warehouse: DF.Check
		status: DF.Literal[
			"Draft", "Submitted", "In Progress", "Completed", "Failed", "Superseded", "Cancelled"
		]
		track_semi_finished_goods: DF.Check
		uom: DF.Link | None
	# end: auto-generated types

	def validate(self):
		if self.has_value_changed("design_file") and self.design_file:
			self.import_design_file()

		self.set_design_name()
		self.item_group = self.item_group or frappe.db.get_single_value("Stock Settings", "item_group")
		self.set_part_structure()
		self.validate_part_models()
		self.validate_finished_good()
		OperationPlan(self).validate()
		self.set_revision_changes()
		MaterialCost(self).set_costs()
		self.set_status()

	def before_submit(self):
		self.validate_operations_have_routing()

	def on_submit(self):
		self.update_previous_revision_status()

	def before_update_after_submit(self):
		self.validate_cad_parts_unchanged()
		self.set_part_structure()
		self.validate_part_models()
		OperationPlan(self).validate()
		MaterialCost(self).set_costs()

	def before_cancel(self):
		self.set_status()

	def on_cancel(self):
		self.update_previous_revision_status()

	def get_status(self) -> str:
		if self.docstatus == 0:
			return "Draft"

		if self.docstatus == 2:
			return "Cancelled"

		if frappe.db.exists("BOM Creator", {"previous_revision": self.name, "docstatus": 1}):
			return "Superseded"

		if self.get_bom_plan().has_all_boms():
			return "Completed"

		return self.status if self.status in ("In Progress", "Failed") else "Submitted"

	def set_status(self, save: bool = False):
		self.status = self.get_status()
		if save:
			self.db_set("status", self.status, notify=True)

	def update_previous_revision_status(self):
		if self.previous_revision:
			frappe.get_doc("BOM Creator", self.previous_revision).set_status(save=True)

	def set_design_name(self):
		if not self.design_name and self.item_code:
			self.design_name = frappe.get_cached_value("Item", self.item_code, "item_name") or self.item_code

		if not self.design_name:
			frappe.throw(_("Set the Design Name or the Finished Good."), title=_("Missing Design Name"))

	def validate_finished_good(self):
		if self.is_phantom and self.track_semi_finished_goods:
			frappe.throw(_("A phantom BOM cannot produce an item at each operation."))

		if not self.item_code:
			return

		is_stock_item = frappe.get_cached_value("Item", self.item_code, "is_stock_item")
		if is_stock_item and self.is_phantom:
			frappe.throw(_("Phantom BOM cannot be created for stock item {0}.").format(self.item_code))
		elif not is_stock_item and not self.is_phantom:
			frappe.throw(
				_("Non-phantom BOM cannot be created for non-stock item {0}.").format(self.item_code)
			)

	def validate_operations_have_routing(self):
		if self.is_phantom or self.routing or self.track_semi_finished_goods:
			return

		for row in self.items:
			if row.operation:
				frappe.throw(
					_(
						"Row #{0}: Item {1} has Operation {2}. Set a Routing to create BOMs with operations."
					).format(row.idx, bold(row.item_code), bold(row.operation)),
					title=_("Routing Required"),
				)

	def import_design_file(self):
		design = read_design_file(self.design_file)
		self.design_name = self.design_name or design["design_name"]
		self.part_number = self.part_number or design["part_number"]

		old_paths = get_part_paths(self.items)
		old_rows = {old_paths[row.node_id]: row for row in self.items}
		manual_rows = [row for row in self.items if row.source == "Manual"]

		self.set("items", [])
		self.append_cad_parts(design["parts"], 0, (), old_rows)
		self.append_manual_parts(manual_rows, old_paths)

		new_node_ids = {path: node_id for node_id, path in get_part_paths(self.items).items()}
		OperationPlan(self).remap_nodes(
			{node_id: new_node_ids[path] for node_id, path in old_paths.items() if path in new_node_ids}
		)

	def append_cad_parts(self, nodes: list[dict], parent_node_id: int, parent_path: tuple, old_rows: dict):
		for node in nodes:
			path = (*parent_path, node["part_number"])
			row = self.append(
				"items",
				{
					"node_id": len(self.items) + 1,
					"parent_node_id": parent_node_id,
					"part_number": node["part_number"],
					"part_name": node["part_name"],
					"description": node["description"],
					"qty": get_quantity(old_rows.get(path), node["quantity"]),
					"design_quantity": node["quantity"],
					"source": "CAD File",
					"do_not_explode": 1,
					**get_mapping(old_rows.get(path)),
				},
			)
			self.append_cad_parts(node["children"], row.node_id, path, old_rows)

	def append_manual_parts(self, manual_rows: list, old_paths: dict):
		new_node_ids = {path: node_id for node_id, path in get_part_paths(self.items).items()}
		new_node_ids[()] = 0
		for row in manual_rows:
			parent_path = old_paths.get(row.parent_node_id, ())
			if parent_path not in new_node_ids:
				frappe.msgprint(
					_("Part {0} was removed because its assembly is not in the new design file.").format(
						bold(row.part_number)
					)
				)
				continue

			new_row = self.append(
				"items", {**row.as_dict(no_default_fields=True), "node_id": len(self.items) + 1}
			)
			new_row.parent_node_id = new_node_ids[parent_path]
			new_node_ids[old_paths[row.node_id]] = new_row.node_id

	def set_part_structure(self):
		last_node_id = max((row.node_id or 0 for row in self.items), default=0)
		for row in self.items:
			self.set_part_number(row)
			if not row.node_id:
				last_node_id += 1
				row.node_id = last_node_id

		node_ids = {row.node_id for row in self.items}
		for row in self.items:
			if row.parent_node_id and row.parent_node_id not in node_ids:
				frappe.throw(
					_("Row #{0}: Parent Node {1} does not exist.").format(row.idx, row.parent_node_id),
					title=_("Invalid Parent Node"),
				)

		parent_node_ids = {row.parent_node_id for row in self.items}
		for row in self.items:
			row.is_expandable = 1 if row.node_id in parent_node_ids else 0

		get_part_paths(self.items)

	def set_part_number(self, row):
		row.part_number = row.part_number or row.item_code
		if not row.part_number:
			frappe.throw(_("Row #{0}: set the Part Number or the Item.").format(row.idx))

		if not row.part_name and row.item_code:
			row.part_name = row.item_name or frappe.get_cached_value("Item", row.item_code, "item_name")

	def validate_part_models(self):
		for row in self.items:
			if row.model_file and row.model_file.rsplit(".", 1)[-1].lower() not in PART_MODEL_FORMATS:
				frappe.throw(
					_("Row #{0}: attach the 3D model as a STEP, STL or GLB file.").format(row.idx),
					title=_("Invalid 3D Model"),
				)

			if row.placements and not isinstance(frappe.parse_json(row.placements), list):
				frappe.throw(_("Row #{0}: the placements in the model are not valid.").format(row.idx))

	def validate_cad_parts_unchanged(self):
		before = self.get_doc_before_save()
		cad_node_ids = {row.node_id for row in self.items if row.source == "CAD File"}
		removed = [
			row.part_number
			for row in before.items
			if row.source == "CAD File" and row.node_id not in cad_node_ids
		]
		if removed:
			frappe.throw(
				_("Parts from the submitted design file cannot be removed: {0}").format(", ".join(removed)),
				title=_("Not Allowed"),
			)

	def set_revision_changes(self):
		if not self.previous_revision:
			return

		previous_quantities = get_part_quantities(self.get_previous_parts())
		paths = get_part_paths(self.items)
		for row in self.items:
			previous_quantity = previous_quantities.get(paths[row.node_id])
			if previous_quantity is None:
				row.change_type = "Added"
			elif flt(previous_quantity) != get_design_quantity(row):
				row.change_type = "Quantity Changed"
			else:
				row.change_type = ""

	def get_previous_parts(self) -> list:
		return frappe.get_all(
			"BOM Creator Item",
			filters={"parent": self.previous_revision, "parenttype": "BOM Creator"},
			fields=["node_id", "parent_node_id", "part_number", "part_name", "qty", "design_quantity"],
			order_by="idx",
		)

	@frappe.whitelist()
	def get_revision_changes(self) -> dict:
		if not self.previous_revision:
			frappe.throw(_("This design has no previous revision."))

		previous_parts = self.get_previous_parts()
		previous_paths = get_part_paths(previous_parts)
		previous_rows = {previous_paths[row.node_id]: row for row in previous_parts}
		current_paths = get_part_paths(self.items)
		changes = {"added": [], "removed": [], "quantity_changed": []}

		for row in self.items:
			path = current_paths[row.node_id]
			previous = previous_rows.pop(path, None)
			if not previous:
				changes["added"].append(get_change(row, path, None))
			elif get_design_quantity(previous) != get_design_quantity(row):
				changes["quantity_changed"].append(get_change(row, path, previous))

		changes["removed"] = [get_change(None, path, row) for path, row in previous_rows.items()]
		return changes

	@frappe.whitelist(methods=["POST"])
	def make_new_revision(self) -> str:
		self.check_permission("write")
		if self.docstatus != 1:
			frappe.throw(_("Submit this design before making a new revision."))

		if frappe.db.exists("BOM Creator", {"previous_revision": self.name, "docstatus": ("<", 2)}):
			frappe.throw(_("A newer revision of this design already exists."))

		revision = frappe.copy_doc(self, ignore_no_copy=False)
		revision.docstatus = 0
		revision.revision = self.revision + 1
		revision.previous_revision = self.name
		revision.insert()
		return revision.name

	def get_bom_plan(self) -> OperationPlan | PartTreePlan:
		return OperationPlan(self) if self.track_semi_finished_goods else PartTreePlan(self)

	def get_used_parts(self) -> list:
		node_ids = self.get_bom_plan().get_used_node_ids()
		return [row for row in self.items if row.node_id in node_ids]

	@frappe.whitelist()
	def get_suggested_items(self) -> dict:
		rows = [row for row in self.items if not row.item_code]
		item_codes = set(
			frappe.get_all(
				"Item",
				filters={"name": ("in", [row.part_number for row in rows]), "disabled": 0},
				pluck="name",
			)
		)

		items_by_name = defaultdict(list)
		for item in frappe.get_all(
			"Item",
			filters={"item_name": ("in", [row.part_name for row in rows]), "disabled": 0},
			fields=["name", "item_name"],
		):
			items_by_name[item.item_name].append(item.name)

		suggestions = {}
		for row in rows:
			if row.part_number in item_codes:
				suggestions[row.name] = row.part_number
			elif len(items_by_name.get(row.part_name, [])) == 1:
				suggestions[row.name] = items_by_name[row.part_name][0]

		return suggestions

	@frappe.whitelist(methods=["POST"])
	def create_items(self, item_group: str, stock_uom: str) -> list[str]:
		self.check_permission("write")
		frappe.has_permission("Item", "create", throw=True)

		created = []
		rows = [row for row in self.get_used_parts() if not row.item_code]
		items = get_items_by_code([row.part_number for row in rows])
		for row in rows:
			if row.part_number not in items:
				item_code = make_item(row.part_number, row.part_name, row.description, item_group, stock_uom)
				items[row.part_number] = frappe._dict(name=item_code, stock_uom=stock_uom)
				created.append(item_code)

			row.item_code = items[row.part_number].name
			row.uom = items[row.part_number].stock_uom

		self.save()
		return created

	@frappe.whitelist(methods=["POST"])
	def enqueue_create_boms(self):
		self.check_permission("submit")
		self.validate_can_create_boms()
		self.get_bom_plan().validate_can_make_boms()
		self.db_set({"status": "In Progress", "error_log": None}, notify=True)
		frappe.enqueue_doc(
			"BOM Creator", self.name, "create_boms", queue="short", timeout=600, enqueue_after_commit=True
		)

		frappe.msgprint(_("The BOMs are being created. The status changes when they are ready."), alert=True)

	def validate_can_create_boms(self):
		if self.docstatus != 1:
			frappe.throw(_("Submit this design before creating BOMs."))

		if self.status == "Superseded":
			frappe.throw(_("This design has a newer revision. Create BOMs from the latest revision."))

		if self.status == "Completed":
			frappe.throw(_("BOMs are already created from this design. Cancel them to create them again."))

	def create_boms(self):
		self.db_set({"status": "In Progress", "error_log": None})
		try:
			self.get_bom_plan().make_boms()
		except Exception:
			frappe.db.rollback()
			self.db_set(
				{"status": "Failed", "error_log": frappe.get_traceback(with_context=True)}, notify=True
			)
			return

		self.set_status(save=True)


def read_design_file(file_url: str) -> dict:
	file = frappe.get_doc("File", {"file_url": file_url})
	file.check_permission("read")

	extension = file.file_name.rsplit(".", 1)[-1].lower()
	if extension not in DESIGN_FILE_READERS:
		frappe.throw(_("Attach a STEP file (.step or .stp) or a CSV file."), title=_("Invalid Design File"))

	content = file.get_content()
	if isinstance(content, bytes):
		content = content.decode("utf-8", errors="replace")

	return DESIGN_FILE_READERS[extension](content)


def get_part_paths(parts: list) -> dict[int, tuple]:
	rows = {row.node_id: row for row in parts}
	paths = {}
	for row in parts:
		path, current = [], row
		while current:
			if len(path) > len(rows):
				frappe.throw(_("Part {0} is inside its own assembly.").format(bold(row.part_number)))

			path.append(current.part_number)
			current = rows.get(current.parent_node_id)

		paths[row.node_id] = tuple(reversed(path))

	return paths


def get_part_quantities(parts: list) -> dict[tuple, float]:
	paths = get_part_paths(parts)
	return {paths[row.node_id]: get_design_quantity(row) for row in parts}


def get_change(row, path: tuple, previous) -> dict:
	current = row or previous
	return {
		"part_number": current.part_number,
		"part_name": current.part_name,
		"path": " > ".join(path),
		"previous_quantity": get_design_quantity(previous) if previous else None,
		"quantity": get_design_quantity(row) if row else None,
	}


def get_design_quantity(row) -> float:
	return flt(row.get("design_quantity")) or flt(row.qty)


def get_quantity(old_row, design_quantity: float) -> float:
	if old_row and flt(old_row.qty) != get_design_quantity(old_row):
		return old_row.qty

	return design_quantity


def get_mapping(row) -> dict:
	if not row:
		return {}

	return {field: row.get(field) for field in MAPPING_FIELDS}


def get_items_by_code(item_codes: list[str]) -> dict:
	if not item_codes:
		return {}

	items = frappe.get_all("Item", filters={"name": ("in", item_codes)}, fields=["name", "stock_uom"])
	return {item.name: item for item in items}


def make_item(
	item_code: str, item_name: str, description: str | None, item_group: str, stock_uom: str
) -> str:
	item = frappe.new_doc("Item")
	item.update(
		{
			"item_code": item_code,
			"item_name": item_name or item_code,
			"description": description or item_name or item_code,
			"item_group": item_group,
			"stock_uom": stock_uom,
			"is_stock_item": 1,
			"include_item_in_manufacturing": 1,
		}
	)
	item.insert()
	return item.name

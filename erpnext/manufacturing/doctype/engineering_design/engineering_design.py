# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime

from erpnext.manufacturing.doctype.engineering_design.bom_csv_file import read_bom_csv_file
from erpnext.manufacturing.doctype.engineering_design.operation_plan import OperationPlan
from erpnext.manufacturing.doctype.engineering_design.part_tree_plan import PartTreePlan
from erpnext.manufacturing.doctype.engineering_design.step_file import read_step_file

DESIGN_FILE_READERS = {"step": read_step_file, "stp": read_step_file, "csv": read_bom_csv_file}
PART_MODEL_FORMATS = ("step", "stp", "stl", "glb")
MAPPING_FIELDS = ("item_code", "item_name", "uom", "exclude_from_bom")


class EngineeringDesign(Document):
	def validate(self):
		if self.has_value_changed("design_file") and self.design_file:
			self.import_design_file()

		if not self.design_name:
			frappe.throw(_("Set the Design Name."), title=_("Missing Design Name"))

		self.item_group = self.item_group or frappe.db.get_single_value("Stock Settings", "item_group")

		self.set_part_structure()
		self.validate_part_models()
		OperationPlan(self).validate()
		self.set_revision_changes()
		self.set_status()

	def before_submit(self):
		self.approved_by = frappe.session.user
		self.approved_on = now_datetime()

	def on_submit(self):
		self.update_previous_revision_status()

	def before_update_after_submit(self):
		self.validate_cad_parts_unchanged()
		self.set_part_structure()
		self.validate_part_models()
		OperationPlan(self).validate()

	def before_cancel(self):
		self.set_status()

	def on_cancel(self):
		self.update_previous_revision_status()

	def get_status(self) -> str:
		if self.docstatus == 0:
			return "Draft"

		if self.docstatus == 2:
			return "Cancelled"

		if frappe.db.exists("Engineering Design", {"previous_revision": self.name, "docstatus": 1}):
			return "Superseded"

		return "Completed" if self.boms else "Approved"

	def set_status(self, update: bool = False):
		status = self.get_status()
		if update:
			self.db_set("status", status)
		else:
			self.status = status

	def update_previous_revision_status(self):
		if self.previous_revision:
			frappe.get_doc("Engineering Design", self.previous_revision).set_status(update=True)

	def import_design_file(self):
		design = read_design_file(self.design_file)
		self.design_name = self.design_name or design["design_name"]
		self.part_number = self.part_number or design["part_number"]

		old_paths = get_part_paths(self.parts)
		old_rows = {old_paths[row.node_id]: row for row in self.parts}
		manual_rows = [row for row in self.parts if row.source == "Manual"]

		self.set("parts", [])
		self.append_cad_parts(design["parts"], 0, (), old_rows)
		self.append_manual_parts(manual_rows, old_paths)

		new_node_ids = {path: node_id for node_id, path in get_part_paths(self.parts).items()}
		OperationPlan(self).remap_nodes(
			{node_id: new_node_ids[path] for node_id, path in old_paths.items() if path in new_node_ids}
		)

	def append_cad_parts(self, nodes: list[dict], parent_node_id: int, parent_path: tuple, old_rows: dict):
		for node in nodes:
			path = (*parent_path, node["part_number"])
			row = self.append(
				"parts",
				{
					"node_id": len(self.parts) + 1,
					"parent_node_id": parent_node_id,
					"part_number": node["part_number"],
					"part_name": node["part_name"],
					"description": node["description"],
					"quantity": get_quantity(old_rows.get(path), node["quantity"]),
					"design_quantity": node["quantity"],
					"source": "CAD File",
					**get_mapping(old_rows.get(path)),
				},
			)
			self.append_cad_parts(node["children"], row.node_id, path, old_rows)

	def append_manual_parts(self, manual_rows: list, old_paths: dict):
		new_node_ids = {path: node_id for node_id, path in get_part_paths(self.parts).items()}
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
				"parts", {**row.as_dict(no_default_fields=True), "node_id": len(self.parts) + 1}
			)
			new_row.parent_node_id = new_node_ids[parent_path]
			new_node_ids[old_paths[row.node_id]] = new_row.node_id

	def set_part_structure(self):
		last_node_id = max((row.node_id or 0 for row in self.parts), default=0)
		for row in self.parts:
			if not row.node_id:
				last_node_id += 1
				row.node_id = last_node_id

		node_ids = {row.node_id for row in self.parts}
		for row in self.parts:
			if row.parent_node_id and row.parent_node_id not in node_ids:
				frappe.throw(
					_("Row #{0}: Parent Node {1} does not exist.").format(row.idx, row.parent_node_id),
					title=_("Invalid Parent Node"),
				)

		parent_node_ids = {row.parent_node_id for row in self.parts}
		for row in self.parts:
			row.is_assembly = 1 if row.node_id in parent_node_ids else 0

		get_part_paths(self.parts)

	def validate_part_models(self):
		for row in self.parts:
			if row.model_file and row.model_file.rsplit(".", 1)[-1].lower() not in PART_MODEL_FORMATS:
				frappe.throw(
					_("Row #{0}: attach the 3D model as a STEP, STL or GLB file.").format(row.idx),
					title=_("Invalid 3D Model"),
				)

			if row.placements and not isinstance(frappe.parse_json(row.placements), list):
				frappe.throw(_("Row #{0}: the placements in the model are not valid.").format(row.idx))

	def validate_cad_parts_unchanged(self):
		before = self.get_doc_before_save()
		cad_node_ids = {row.node_id for row in self.parts if row.source == "CAD File"}
		removed = [
			row.part_number
			for row in before.parts
			if row.source == "CAD File" and row.node_id not in cad_node_ids
		]
		if removed:
			frappe.throw(
				_("Parts from the approved design file cannot be removed: {0}").format(", ".join(removed)),
				title=_("Not Allowed"),
			)

	def set_revision_changes(self):
		if not self.previous_revision:
			return

		previous_quantities = get_part_quantities(self.get_previous_parts())
		paths = get_part_paths(self.parts)
		for row in self.parts:
			previous_quantity = previous_quantities.get(paths[row.node_id])
			if previous_quantity is None:
				row.change_type = "Added"
			elif flt(previous_quantity) != get_design_quantity(row):
				row.change_type = "Quantity Changed"
			else:
				row.change_type = ""

	def get_previous_parts(self) -> list:
		return frappe.get_all(
			"Engineering Design Part",
			filters={"parent": self.previous_revision, "parenttype": "Engineering Design"},
			fields=[
				"node_id",
				"parent_node_id",
				"part_number",
				"part_name",
				"quantity",
				"design_quantity",
				*MAPPING_FIELDS,
			],
			order_by="idx",
		)

	@frappe.whitelist()
	def get_revision_changes(self) -> dict:
		if not self.previous_revision:
			frappe.throw(_("This design has no previous revision."))

		previous_parts = self.get_previous_parts()
		previous_paths = get_part_paths(previous_parts)
		previous_rows = {previous_paths[row.node_id]: row for row in previous_parts}
		current_paths = get_part_paths(self.parts)
		changes = {"added": [], "removed": [], "quantity_changed": []}

		for row in self.parts:
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
			frappe.throw(_("Approve this design before making a new revision."))

		if frappe.db.exists("Engineering Design", {"previous_revision": self.name, "docstatus": ("<", 2)}):
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
		return [row for row in self.parts if row.node_id in node_ids]

	@frappe.whitelist()
	def get_suggested_items(self) -> dict:
		rows = [row for row in self.parts if not row.item_code]
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
		if not self.item_code:
			self.item_code = self.get_or_make_finished_good(item_group, stock_uom)
			created.append(self.item_code)

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

	def get_or_make_finished_good(self, item_group: str, stock_uom: str) -> str:
		item_code = self.part_number or self.design_name
		if get_items_by_code([item_code]):
			return item_code

		return make_item(item_code, self.design_name, None, item_group, stock_uom)

	@frappe.whitelist(methods=["POST"])
	def create_boms(self) -> list[str]:
		self.validate_can_create_boms()
		boms = self.get_bom_plan().make_boms()
		self.set("boms", [{"item_code": item_code, "bom": bom} for item_code, bom in boms.items()])
		self.save()
		self.set_status(update=True)
		return list(boms.values())

	def validate_can_create_boms(self):
		if self.docstatus != 1:
			frappe.throw(_("Approve this design before creating BOMs."))

		if self.status == "Superseded":
			frappe.throw(_("This design has a newer revision. Create BOMs from the latest revision."))

		boms = [row.bom for row in self.boms]
		if boms and frappe.db.exists("BOM", {"name": ("in", boms), "docstatus": 1}):
			frappe.throw(_("BOMs are already created from this design. Cancel them to create them again."))


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
	return flt(row.get("design_quantity")) or flt(row.quantity)


def get_quantity(old_row, design_quantity: float) -> float:
	if old_row and flt(old_row.quantity) != get_design_quantity(old_row):
		return old_row.quantity

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

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt
from frappe.utils.csvutils import read_csv_content

COLUMNS = {
	"level": "level",
	"item number": "item_number",
	"part number": "part_number",
	"part name": "part_name",
	"description": "description",
	"quantity": "quantity",
}


def read_bom_csv_file(content: str | bytes) -> dict:
	rows = read_csv_content(content)
	if len(rows) < 2:
		frappe.throw(_("The CSV file has no parts."), title=_("Invalid Design File"))

	columns = [COLUMNS.get(cstr(header).strip().lower()) for header in rows[0]]
	validate_columns(columns)
	parts = [get_part(dict(zip(columns, row, strict=False))) for row in rows[1:] if any(row)]
	return {"design_name": None, "part_number": None, "parts": build_tree(parts)}


def validate_columns(columns: list):
	if "level" not in columns and "item_number" not in columns:
		frappe.throw(
			_("The CSV file needs a Level or an Item Number column."), title=_("Invalid Design File")
		)

	if "part_number" not in columns and "part_name" not in columns:
		frappe.throw(
			_("The CSV file needs a Part Number or a Part Name column."), title=_("Invalid Design File")
		)


def get_part(values: dict) -> dict:
	part_number = cstr(values.get("part_number")).strip()
	part_name = cstr(values.get("part_name")).strip()
	return {
		"depth": get_depth(values),
		"part_number": part_number or part_name,
		"part_name": part_name or part_number,
		"description": cstr(values.get("description")).strip(),
		"quantity": flt(values.get("quantity")) or 1,
		"children": [],
	}


def get_depth(values: dict) -> int:
	if values.get("level") is not None:
		return cint(values.get("level"))

	return cstr(values.get("item_number")).strip().count(".") + 1


def build_tree(parts: list[dict]) -> list[dict]:
	roots, ancestors = [], []
	for row_no, part in enumerate(parts, start=2):
		depth = part.pop("depth")
		if depth < 1 or depth > len(ancestors) + 1:
			frappe.throw(
				_("Row {0}: level {1} does not follow the level of the row above.").format(row_no, depth),
				title=_("Invalid Design File"),
			)

		del ancestors[depth - 1 :]
		siblings = ancestors[-1]["children"] if ancestors else roots
		siblings.append(part)
		ancestors.append(part)

	return roots

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import frappe
from frappe.model.document import Document


class ProductionLine(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		is_active: DF.Check
		is_group: DF.Check
		line_code: DF.Data
		line_name: DF.Data
		parent_line: DF.Link | None
	# end: auto-generated types
	pass


@frappe.whitelist()
def get_parent_line(line_name: str):
	if not line_name:
		return None
	line: ProductionLine = frappe.get_doc("Production Line", line_name)  # pyright: ignore[reportAssignmentType]
	return line.parent_line


@frappe.whitelist()
def get_all_child_lines(line_name: str):
	if not line_name:
		return None
	lines: list[ProductionLine] = frappe.get_all("Production Line", filters={"parent_line": line_name})
	return [line.name for line in lines]

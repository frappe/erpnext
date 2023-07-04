from typing import Optional

import frappe
from frappe import _
from frappe.utils import get_link_to_form


def sanitize_expression(string: Optional[str] = None) -> Optional[str]:
	if not string:
		return None

	# remove forward and trailing spaces, newlines and other line boundaries
	parts = string.strip().splitlines()
	string = " ".join(parts)

	return string


def prepare_error_msg(*, row: dict, error: str, expression: str, description: str) -> str:
	data = frappe._dict(
		{
			"doctype": row.parenttype,
			"doclink": get_link_to_form(row.parenttype, row.parent),
			"parentfield": row.parentfield.title(),
			"row_id": row.idx,
			"expression": expression,
			"error": error,
			"description": description or "",
		}
	)

	return _(
		"Error in {parentfield}, while evaluating the {doctype} {doclink} at row {row_id}. <br><br> <b>Expression:</b> {expression}. <br><br> <b>Error:</b> {error} <br><br> <b>Hint:</b> {description}"
	).format(**data)

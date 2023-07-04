import frappe
from frappe import _
from frappe.utils import get_link_to_form


def sanitize_condition_and_formula(string: str) -> str:
	if not string:
		return " "

	# remove forward and trailing spaces, newlines and other line boundaries
	parts = string.strip().splitlines()
	string = " ".join(parts)

	return string

def prepare_error_msg(*, row: dict, error: str, title: str, description: str):
	data = frappe._dict(
		{
			"doctype": row.parenttype,
			"name": row.parent,
			"doclink": get_link_to_form(row.parenttype, row.parent),
			"row_id": row.idx,
			"error": error,
			"title": title,
			"description": description or "",
		}
	)

	message = _(
		"Error while evaluating the {doctype} {doclink} at row {row_id}. <br><br> <b>Error:</b> {error} <br><br> <b>Hint:</b> {description}"
	).format(**data)

	frappe.throw(message, title=title)
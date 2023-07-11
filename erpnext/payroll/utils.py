from typing import Optional

import frappe
from frappe import _
from frappe.utils import get_link_to_form


def sanitize_expression(string: Optional[str] = None) -> Optional[str]:
	"""
	Sanitizes an expression string by removing leading/trailing spaces, newlines, and line boundaries.

	Args:
	    string (Optional[str]): The input string to be sanitized (default: None).

	Returns:
	    Optional[str]: The sanitized string or None if the input string is empty or None.

	Example:
	    expression = "\r\n    gross_pay > 10000\n    "
	    sanitized_expr = sanitize_expression(expression)
	"""
	if not string:
		return None

	parts = string.strip().splitlines()
	string = " ".join(parts)

	return string


def prepare_error_msg(*, row: dict, error: str, expression: str, description: str) -> str:
	"""
	Prepares an error message string with formatted information about the error.

	Args:
	    row (dict): A dictionary representing the row data.
	    error (str): The error message.
	    expression (str): The expression that caused the error.
	    description (str): Additional description or hint for the error (optional).

	Returns:
	    str: The formatted error message string.

	Example:
	    row = {
	        "parenttype": "Salary Structure",
	        "parent": "Salary Structure-00001",
	        "parentfield": "earnings",
	        "idx": 1
	    }
	    error = "SyntaxError: invalid syntax"
	    expression = " 200 if (gross_pay>10000 and month!=  'Feb')) else 0 "
	    description = "Check the syntax of the expression."
	    error_msg = prepare_error_msg(row=row, error=error, expression=expression, description=description)
	"""
	# Create a dictionary to store the error message data
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

	# Format and return the error message string
	return _(
		"Error in {parentfield}, while evaluating the {doctype} {doclink} at row {row_id}. <br><br> <b>Expression:</b> {expression}. <br><br> <b>Error:</b> {error} <br><br> <b>Hint:</b> {description}"
	).format(**data)

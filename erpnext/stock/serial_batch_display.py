"""Display physical numbers while retaining document IDs for stock references."""

from copy import copy
from functools import wraps

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html

from erpnext.stock.serial_batch_identity import SerialBatchIdentity


def format_serial_batch_numbers(doctype: str, names: list[str]) -> str:
	labels = SerialBatchIdentity(doctype).labels(names)
	return ", ".join(escape_html(labels.get(name) or name) for name in names)


def with_serial_batch_numbers(execute):
	@wraps(execute)
	def wrapped(*args, **kwargs):
		result = execute(*args, **kwargs)
		if not result or len(result) < 2:
			return result
		columns, rows, *other = result
		columns, rows = report_number_columns(columns, rows)
		return columns, rows, *other

	return wrapped


def report_number_columns(columns, rows):
	from frappe.desk.query_report import get_column_as_dict

	columns = [get_column_as_dict(column) for column in columns]
	rows = [list(row) if isinstance(row, list | tuple) else row.copy() for row in rows]
	for index, column in enumerate(list(columns)):
		doctype = column.get("options")
		field = column["fieldname"]
		if doctype not in ("Serial No", "Batch"):
			if field in ("serial_no", "balance_serial_no"):
				doctype = "Serial No"
			else:
				continue
		values = [row.get(field) if isinstance(row, dict) else row[index] for row in rows]
		names = {name for value in values if value for name in str(value).split("\n")}
		labels = SerialBatchIdentity(doctype).labels(names)
		number_field = f"{field}_number"
		columns.append({**column, "hidden": 1, "label": _("{0} ID").format(column["label"])})
		columns[index] = {
			"fieldname": number_field,
			"label": column["label"],
			"fieldtype": "Serial Batch Number",
			"options": doctype,
			"reference_field": field,
			"width": column.get("width", 140),
			"hidden": column.get("hidden", 0),
		}
		for row, value in zip(rows, values, strict=True):
			number = "\n".join(labels.get(name, name) for name in str(value).split("\n")) if value else value
			if isinstance(row, dict):
				row[number_field] = number
			else:
				row.append(value)
				row[index] = number
	return columns, rows


class SerialBatchReference(Document):
	def get_formatted(
		self, fieldname, doc=None, currency=None, absolute_value=False, translated=False, format=None
	):
		if fieldname not in serial_number_fields(self) or not self.get(fieldname):
			return super().get_formatted(fieldname, doc, currency, absolute_value, translated, format)

		names = self.get(fieldname).split("\n")
		labels = {}
		if fieldname not in (self.get("__serial_batch_input") or []):
			labels = self.get("__serial_number_labels") or {}
			if any(name not in labels for name in names):
				set_serial_number_labels(self.parent_doc or self)
				labels = self.get("__serial_number_labels") or {}

		print_row = copy(self)
		print_row.set(fieldname, "\n".join(escape_html(labels.get(name, name)) for name in names))
		return super(SerialBatchReference, print_row).get_formatted(
			fieldname, doc, currency, absolute_value, translated, format
		)


def set_serial_number_labels(doc, method=None, print_settings=None):
	rows = [row for row in [doc, *doc.get_all_children()] if isinstance(row, SerialBatchReference)]
	names = {
		name
		for row in rows
		for field in serial_number_fields(row)
		if row.get(field) and field not in (row.get("__serial_batch_input") or [])
		for name in row.get(field).split("\n")
	}
	labels = SerialBatchIdentity("Serial No").labels(names)
	labels = {name: labels.get(name) or name for name in names}
	for row in rows:
		row.__dict__["__serial_number_labels"] = labels


def serial_number_fields(row):
	return [
		field
		for field in ("serial_no", "rejected_serial_no", "current_serial_no")
		if (meta := row.meta.get_field(field)) and meta.fieldtype in ("Small Text", "Text", "Long Text")
	]

"""Display physical numbers while retaining document IDs for stock references."""

from copy import deepcopy
from functools import wraps

import frappe
from frappe import _
from frappe.utils import escape_html

from erpnext.stock.serial_batch_identity import SerialBatchIdentity


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


def pdf_body_html(template, args, **kwargs):
	from frappe.utils.pdf import pdf_body_html as render_body

	print_doc = deepcopy(args["doc"])
	set_serial_number_labels(print_doc)
	return render_body(template, {**args, "doc": print_doc}, **kwargs)


def set_serial_number_labels(doc):
	rows = [doc, *doc.get_all_children()]
	fields = ("serial_no", "rejected_serial_no", "current_serial_no")
	serial_rows = [
		row
		for row in rows
		if row.doctype != "Serial No" and (row.get("item_code") or row.get("rm_item_code"))
	]
	values = []
	for row in serial_rows:
		for field in fields:
			meta = row.meta.get_field(field)
			if meta and meta.fieldtype in ("Small Text", "Text", "Long Text") and row.get(field):
				values.append((row, field, row.get(field).split("\n")))
	labels = SerialBatchIdentity("Serial No").labels([name for _, _, names in values for name in names])
	for row, field, names in values:
		row.set(field, "\n".join(escape_html(labels.get(name, name)) for name in names))

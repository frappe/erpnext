import frappe
from frappe import _
from frappe.desk.query_report import get_column_as_dict, normalize_result

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.serial_batch_identity import SerialBatchIdentity


def prepare_serial_batch_report(columns, data, *, serial_fields=()):
	"""Add physical labels to report results. serial_fields explicitly identifies multiline ID text."""
	columns = [get_column_as_dict(column) for column in columns]
	data = [frappe._dict(row) for row in normalize_result(data or [], columns)]
	number_columns = prepare_number_columns(columns, serial_fields)
	set_number_labels(data, number_columns)
	return columns, data


def prepare_number_columns(columns, serial_fields):
	number_columns = []
	fieldnames = {column.fieldname for column in columns}
	for column in columns.copy():
		multiple = column.fieldname in serial_fields
		doctype = column.options if column.fieldtype == "Link" else None
		if multiple:
			doctype = "Serial No"
		if doctype not in ("Serial No", "Batch"):
			continue

		fieldname = column.fieldname
		number_field = f"{fieldname}_number"
		if number_field in fieldnames:
			frappe.throw(_("Report already contains column {0}").format(frappe.bold(number_field)))
		columns.append({**column, "label": _("{0} ID").format(column.label), "hidden": 1})
		column.update(
			fieldname=number_field,
			fieldtype="Data",
			options=None,
			serial_batch={"doctype": doctype, "fieldname": fieldname, "multiple": multiple},
		)
		number_columns.append(column)
	return number_columns


def set_number_labels(data, columns):
	for doctype in ("Serial No", "Batch"):
		doctype_columns = [column for column in columns if column.serial_batch["doctype"] == doctype]
		names = set()
		for column in doctype_columns:
			for row in data:
				names.update(get_reference_ids(row, column.serial_batch))
		numbers = SerialBatchIdentity(doctype).get_number_map(names)
		for column in doctype_columns:
			for row in data:
				row[column.fieldname] = "\n".join(
					numbers.get(name, name) for name in get_reference_ids(row, column.serial_batch)
				)


def get_reference_ids(row, reference):
	value = row.get(reference["fieldname"])
	if reference["multiple"]:
		return get_serial_nos(value)
	return [value] if value else []

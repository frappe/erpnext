# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	"""Return columns for the report.

	One field definition per column, just like a DocType field definition.
	"""
	return [
		{
			"label": _("Serial and Batch Bundle"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Serial and Batch Bundle",
			"width": 200,
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 200,
		},
		{
			"label": _("Voucher Detail No"),
			"fieldname": "voucher_detail_no",
			"fieldtype": "Data",
			"width": 200,
		},
	]


def get_data(filters) -> list[list]:
	"""Return data for the report.

	The report data is a list of rows, with each row being a list of cell values.
	"""

	SABB = frappe.qb.DocType("Serial And Batch Bundle")
	SLE = frappe.qb.DocType("Stock Ledger Entry")
	ignore_voycher_types = [
		"Installation Note",
		"Job Card",
		"Maintenance Schedule",
		"Pick List",
	]

	query = (
		frappe.qb.from_(SABB)
		.left_join(SLE)
		.on(SABB.name == SLE.serial_and_batch_bundle)
		.select(
			SABB.name,
			SABB.voucher_type,
			SABB.voucher_no,
			SABB.voucher_detail_no,
		)
		.where(
			(SLE.serial_and_batch_bundle.isnull())
			& (SABB.docstatus == 1)
			& (SABB.is_cancelled == 0)
			& (SABB.voucher_type.notin(ignore_voycher_types))
		)
	)

	for field in filters:
		query = query.where(SABB[field] == filters[field])

	data = query.run(as_dict=1)

	return data


@frappe.whitelist()
def remove_sabb_entry(selected_rows):
	if isinstance(selected_rows, str):
		selected_rows = frappe.parse_json(selected_rows)

	for row in selected_rows:
		doc = frappe.get_doc("Serial and Batch Bundle", row.get("name"))
		doc.cancel()
		doc.delete()

	frappe.msgprint(_("Selected Serial and Batch Bundle entries have been removed."))

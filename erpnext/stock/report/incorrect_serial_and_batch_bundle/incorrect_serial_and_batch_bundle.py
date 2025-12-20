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
	unlinked_bundles = get_unlinked_serial_batch_bundles(filters) or []
	linked_cancelled_bundles = get_linked_cancelled_sabb(filters) or []

	data = unlinked_bundles + linked_cancelled_bundles

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
		{
			"label": _("Is Cancelled"),
			"fieldname": "is_cancelled",
			"fieldtype": "Check",
			"width": 200,
		},
	]


def get_unlinked_serial_batch_bundles(filters) -> list[list]:
	# SABB has not been linked to any SLE

	SABB = frappe.qb.DocType("Serial and Batch Bundle")
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
			SABB.is_cancelled,
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


def get_linked_cancelled_sabb(filters):
	# SABB has cancelled but voucher is not cancelled

	SABB = frappe.qb.DocType("Serial and Batch Bundle")
	SLE = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(SABB)
		.inner_join(SLE)
		.on(SABB.name == SLE.serial_and_batch_bundle)
		.select(
			SABB.name,
			SABB.voucher_type,
			SABB.voucher_no,
			SABB.voucher_detail_no,
			SABB.is_cancelled,
		)
		.where(
			(SLE.serial_and_batch_bundle.isnotnull())
			& (SABB.docstatus == 2)
			& (SABB.is_cancelled == 1)
			& (SLE.is_cancelled == 0)
		)
	)

	for field in filters:
		query = query.where(SABB[field] == filters[field])

	data = query.run(as_dict=1)
	return data


@frappe.whitelist()
def fix_sabb_entries(selected_rows):
	if isinstance(selected_rows, str):
		selected_rows = frappe.parse_json(selected_rows)

	for row in selected_rows:
		doc = frappe.get_doc("Serial and Batch Bundle", row.get("name"))
		if doc.is_cancelled == 0 and not frappe.db.get_value(
			"Stock Ledger Entry",
			{"serial_and_batch_bundle": doc.name, "is_cancelled": 0},
			"name",
		):
			doc.db_set({"is_cancelled": 1, "docstatus": 2})

			for row in doc.entries:
				row.db_set("docstatus", 2)

		elif doc.is_cancelled == 1 and frappe.db.get_value(
			"Stock Ledger Entry",
			{"serial_and_batch_bundle": doc.name, "is_cancelled": 0},
			"name",
		):
			doc.db_set({"is_cancelled": 0, "docstatus": 1})

			for row in doc.entries:
				row.db_set("docstatus", 1)

	frappe.msgprint(_("Selected Serial and Batch Bundle entries have been fixed."))

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Sum
from frappe.utils import cint, flt, parse_json

from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	create_serial_batch_no_ledgers,
	get_type_of_transaction,
	make_batch_nos,
	make_serial_nos,
)

SUPPORTED_VOUCHER_TYPES = frozenset(
	[
		"Purchase Receipt",
		"Purchase Invoice",
		"Sales Invoice",
		"POS Invoice",
		"Delivery Note",
		"Stock Entry",
		"Stock Reconciliation",
		"Subcontracting Receipt",
		"Pick List",
		"Asset Capitalization",
		"Asset Repair",
	]
)


@frappe.whitelist()
def get_bundle_entries(bundle: str, start: int = 0, page_length: int = 50, search: str | None = None):
	frappe.has_permission("Serial and Batch Bundle", "read", doc=bundle, throw=True)
	page_length = min(cint(page_length) or 50, 500)

	table = frappe.qb.DocType("Serial and Batch Entry")
	query = (
		frappe.qb.from_(table)
		.select(table.name, table.serial_no, table.batch_no, table.qty)
		.where(table.parent == bundle)
		.orderby(table.idx)
		.limit(page_length)
		.offset(cint(start))
	)

	if search:
		search_term = f"%{search}%"
		query = query.where((table.serial_no.like(search_term)) | (table.batch_no.like(search_term)))

	entries = query.run(as_dict=True)
	summary = get_bundle_summary(bundle)
	summary["entries"] = entries

	return summary


def get_bundle_summary(bundle):
	table = frappe.qb.DocType("Serial and Batch Entry")
	row = (
		frappe.qb.from_(table)
		.select(Count(table.name).as_("total_count"), Sum(table.qty).as_("total_qty"))
		.where(table.parent == bundle)
	).run(as_dict=True)[0]

	return frappe._dict(
		{
			"bundle": bundle,
			"total_count": cint(row.total_count),
			"total_qty": abs(flt(row.total_qty)),
		}
	)


@frappe.whitelist()
def download_bundle_entries_csv(bundle: str):
	from frappe.utils.csvutils import build_csv_response

	frappe.has_permission("Serial and Batch Bundle", "read", doc=bundle, throw=True)
	doc = frappe.get_doc("Serial and Batch Bundle", bundle)
	item = frappe.get_cached_value("Item", doc.item_code, ["has_serial_no", "has_batch_no"], as_dict=True)

	rows = [get_csv_columns(item)]
	for entry in doc.entries:
		if item.has_serial_no and item.has_batch_no:
			rows.append([entry.serial_no, entry.batch_no, abs(entry.qty)])
		elif item.has_batch_no:
			rows.append([entry.batch_no, abs(entry.qty)])
		else:
			rows.append([entry.serial_no])

	build_csv_response(rows, f"{bundle}-entries")


def get_csv_columns(item):
	if item.has_serial_no and item.has_batch_no:
		return ["Serial No", "Batch No", "Quantity"]

	if item.has_batch_no:
		return ["Batch No", "Quantity"]

	return ["Serial No"]


@frappe.whitelist(methods=["POST"])
def upsert_bundle_entries(
	child_row: dict | str,
	doc: dict | str,
	entries: list | str | None = None,
	deleted: list | str | None = None,
	replace: int = 0,
):
	child_row = parse_json(child_row)
	doc = parse_json(doc)
	entries = parse_json(entries) or []
	deleted = parse_json(deleted) or []

	validate_parent_document(child_row, doc)

	bundle_field = (
		"rejected_serial_and_batch_bundle" if child_row.get("is_rejected") else "serial_and_batch_bundle"
	)
	bundle_name = child_row.get(bundle_field)
	if bundle_name and frappe.db.exists("Serial and Batch Bundle", bundle_name):
		bundle = apply_incremental_changes(bundle_name, child_row, entries, deleted, cint(replace))
		if not bundle.entries:
			remove_empty_bundle(bundle, child_row, bundle_field)
			return frappe._dict({"bundle": None, "total_count": 0, "total_qty": 0})
	else:
		if not entries:
			frappe.throw(_("Please add at least one Serial No or Batch to save"))

		frappe.has_permission(doc.get("doctype"), "write", throw=True)
		if get_type_of_transaction(doc, child_row) == "Inward":
			make_serial_nos(child_row.item_code, entries)
			make_batch_nos(child_row.item_code, entries)

		bundle = create_serial_batch_no_ledgers(entries, child_row, doc)

	return get_bundle_summary(bundle.name)


def validate_parent_document(child_row, doc):
	if doc.get("doctype") not in SUPPORTED_VOUCHER_TYPES:
		frappe.throw(
			_("{0} is not supported for the inline Serial / Batch editor").format(doc.get("doctype"))
		)

	if child_row.get("parenttype") != doc.get("doctype"):
		frappe.throw(_("The selected row does not belong to the {0}").format(doc.get("doctype")))


def remove_empty_bundle(bundle, child_row, bundle_field):
	child_doctype, child_name = child_row.get("doctype"), child_row.get("name")
	if (
		child_name
		and child_doctype
		and frappe.get_meta(child_doctype).has_field(bundle_field)
		and frappe.db.exists(child_doctype, {"name": child_name, bundle_field: bundle.name})
	):
		frappe.db.set_value(child_doctype, child_name, bundle_field, None)

	bundle.delete(ignore_permissions=True)


def apply_incremental_changes(bundle_name, child_row, entries, deleted, replace=0):
	frappe.has_permission("Serial and Batch Bundle", "write", doc=bundle_name, throw=True)
	bundle = frappe.get_doc("Serial and Batch Bundle", bundle_name)

	if bundle.docstatus == 1:
		frappe.throw(
			_("Serial and Batch Bundle {0} is submitted and its entries cannot be modified.").format(
				frappe.bold(bundle_name)
			)
		)

	sign = 1 if bundle.type_of_transaction == "Inward" else -1

	if replace:
		bundle.set("entries", [])
		deleted = []
		entries = [{key: value for key, value in row.items() if key != "name"} for row in entries]

	if deleted:
		bundle.entries = [d for d in bundle.entries if d.name not in deleted]

	existing = {d.name: d for d in bundle.entries}
	new_rows = [frappe._dict(row) for row in entries if not row.get("name")]

	for row in entries:
		if row.get("name") and row["name"] in existing:
			entry = existing[row["name"]]
			if row.get("qty") is not None:
				entry.qty = (flt(row.get("qty")) or 1.0) * sign
			if row.get("batch_no"):
				entry.batch_no = row.get("batch_no")
			if row.get("serial_no"):
				entry.serial_no = row.get("serial_no")

	if entries and bundle.type_of_transaction == "Inward":
		incoming = [frappe._dict(row) for row in entries]
		make_serial_nos(child_row.item_code, incoming)
		make_batch_nos(child_row.item_code, incoming)

	for row in new_rows:
		bundle.append(
			"entries",
			{
				"qty": (flt(row.qty) or 1.0) * sign,
				"warehouse": bundle.warehouse,
				"batch_no": row.batch_no,
				"serial_no": row.serial_no,
			},
		)

	if not bundle.entries:
		return bundle

	bundle.save(ignore_permissions=True)
	return bundle

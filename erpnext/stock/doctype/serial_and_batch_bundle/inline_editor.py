# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Lower, Sum
from frappe.utils import cint, flt, parse_json

from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	create_serial_batch_no_ledgers,
	get_type_of_transaction,
)
from erpnext.stock.serial_batch_identity import SerialBatchIdentity

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
		serial = frappe.qb.DocType("Serial No")
		batch = frappe.qb.DocType("Batch")
		search_term = f"%{search.lower()}%"
		query = (
			query.left_join(serial)
			.on(table.serial_no == serial.name)
			.left_join(batch)
			.on(table.batch_no == batch.name)
			.where(Lower(serial.serial_no).like(search_term) | Lower(batch.batch_id).like(search_term))
		)

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
	item_code = frappe.db.get_value("Serial and Batch Bundle", bundle, "item_code")
	item = frappe.get_cached_value("Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=True)
	entries = frappe.get_all(
		"Serial and Batch Entry",
		filters={"parent": bundle},
		fields=["serial_no.serial_no as serial_no", "batch_no.batch_id as batch_no", "qty"],
		order_by="idx",
	)

	rows = [get_csv_columns(item)]
	for entry in entries:
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
	serial_numbers: list | str | None = None,
	batch_numbers: list | str | None = None,
	csv_entries: list | str | None = None,
):
	child_row = parse_json(child_row)
	doc = parse_json(doc)
	entries = parse_json(entries) or []
	deleted = parse_json(deleted) or []
	serial_numbers = parse_json(serial_numbers) or []
	batch_numbers = parse_json(batch_numbers) or []
	csv_entries = parse_json(csv_entries) or []

	validate_parent_document(child_row, doc)

	bundle_field = (
		"rejected_serial_and_batch_bundle" if child_row.get("is_rejected") else "serial_and_batch_bundle"
	)
	bundle_name = child_row.get(bundle_field)
	if bundle_name and frappe.db.exists("Serial and Batch Bundle", bundle_name):
		bundle = apply_incremental_changes(
			bundle_name,
			child_row,
			entries,
			deleted,
			cint(replace),
			serial_numbers,
			batch_numbers,
			csv_entries,
		)
		if not bundle.entries:
			remove_empty_bundle(bundle, child_row, bundle_field)
			return frappe._dict({"bundle": None, "total_count": 0, "total_qty": 0})
	else:
		if not entries and not serial_numbers and not batch_numbers and not csv_entries:
			frappe.throw(_("Please add at least one Serial No or Batch to save"))

		frappe.has_permission(doc.get("doctype"), "write", throw=True)
		frappe.has_permission("Serial and Batch Bundle", "create", throw=True)
		type_of_transaction = get_type_of_transaction(doc, child_row)
		entries += resolve_csv_entries(
			csv_entries, child_row.item_code, type_of_transaction, doc.get("company")
		)
		entries = append_scanned_serials(
			entries,
			serial_numbers,
			child_row.item_code,
			type_of_transaction,
			doc.get("company"),
		)
		entries = append_scanned_batches(entries, batch_numbers, child_row.item_code, type_of_transaction)
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


def apply_incremental_changes(
	bundle_name,
	child_row,
	entries,
	deleted,
	replace=0,
	serial_numbers=None,
	batch_numbers=None,
	csv_entries=None,
):
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

	for row in entries:
		if row.get("name") and row["name"] in existing:
			entry = existing[row["name"]]
			if row.get("qty") is not None:
				entry.qty = (flt(row.get("qty")) or 1.0) * sign
			if row.get("batch_no"):
				entry.batch_no = row.get("batch_no")
			if row.get("serial_no"):
				entry.serial_no = row.get("serial_no")

	new_rows = append_scanned_serials(
		[frappe._dict(row) for row in entries if not row.get("name")],
		serial_numbers or [],
		bundle.item_code,
		bundle.type_of_transaction,
		bundle.company,
		[d.serial_no for d in bundle.entries if d.serial_no],
	)
	new_rows += resolve_csv_entries(
		csv_entries or [], bundle.item_code, bundle.type_of_transaction, bundle.company
	)
	new_rows = append_scanned_batches(
		new_rows, batch_numbers or [], bundle.item_code, bundle.type_of_transaction, bundle.entries
	)
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


def append_scanned_serials(entries, scans, item_code, type_of_transaction, company, existing_serials=()):
	if not isinstance(scans, list) or any(not isinstance(scan, dict) for scan in scans):
		frappe.throw(_("Scanned serials must be a list of numbers and batches"))
	numbers_by_batch = defaultdict(list)
	for scan in scans:
		numbers_by_batch[scan.get("batch_no")].append(scan.get("serial_number"))

	entries = [frappe._dict(row) for row in entries]
	known = set(existing_serials) | {row.serial_no for row in entries if row.serial_no}
	for batch_no, numbers in numbers_by_batch.items():
		serial_ids = SerialBatchIdentity("Serial No").resolve(
			item_code,
			numbers,
			create=type_of_transaction == "Inward",
			defaults={"company": company, "batch_no": batch_no},
		)
		for serial_id in serial_ids:
			if serial_id not in known:
				entries.append(frappe._dict(serial_no=serial_id, batch_no=batch_no, qty=1))
				known.add(serial_id)
	return entries


def resolve_csv_entries(rows, item_code, type_of_transaction, company):
	if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
		frappe.throw(_("CSV entries must be a list of rows"))
	entries = [
		frappe._dict(
			serial_no=row.get("serial_no_id"),
			batch_no=row.get("batch_no_id"),
			serial_number=row.get("serial_no"),
			batch_number=row.get("batch_no"),
			qty=row.get("qty"),
		)
		for row in rows
	]
	create = type_of_transaction == "Inward"
	batch_entries = [entry for entry in entries if entry.batch_number and not entry.batch_no]
	batch_ids = SerialBatchIdentity("Batch").resolve(
		item_code, [entry.batch_number for entry in batch_entries], create=create
	)
	for entry, batch_id in zip(batch_entries, batch_ids, strict=True):
		entry.batch_no = batch_id

	serials_by_batch = defaultdict(list)
	for entry in entries:
		if entry.serial_number and not entry.serial_no:
			serials_by_batch[entry.batch_no].append(entry)
	for batch_id, serial_entries in serials_by_batch.items():
		serial_ids = SerialBatchIdentity("Serial No").resolve(
			item_code,
			[entry.serial_number for entry in serial_entries],
			create=create,
			defaults={"company": company, "batch_no": batch_id},
		)
		for entry, serial_id in zip(serial_entries, serial_ids, strict=True):
			entry.serial_no = serial_id
	return [
		frappe._dict({field: entry[field] for field in ("serial_no", "batch_no", "qty")}) for entry in entries
	]


def append_scanned_batches(entries, scans, item_code, type_of_transaction, existing_entries=()):
	if not isinstance(scans, list) or any(not isinstance(scan, dict) for scan in scans):
		frappe.throw(_("Scanned batches must be a list of numbers and quantities"))
	if any(flt(scan.get("qty")) <= 0 for scan in scans):
		frappe.throw(_("Scanned batch quantities must be greater than zero"))
	batch_ids = SerialBatchIdentity("Batch").resolve(
		item_code,
		[scan.get("batch_number") for scan in scans],
		create=type_of_transaction == "Inward",
	)
	entries = [frappe._dict(row) for row in entries]
	by_batch = {
		row.batch_no: row for row in [*entries, *existing_entries] if row.batch_no and not row.serial_no
	}
	for batch_id, scan in zip(batch_ids, scans, strict=True):
		qty = flt(scan.get("qty"))
		if batch_id in by_batch:
			row = by_batch[batch_id]
			current_qty = flt(row.qty)
			row.qty = current_qty - qty if current_qty < 0 else current_qty + qty
		else:
			row = frappe._dict(batch_no=batch_id, qty=qty)
			entries.append(row)
			by_batch[batch_id] = row
	return entries

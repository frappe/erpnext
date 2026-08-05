# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Sum
from frappe.utils import cint, flt, nowtime, parse_json, today

from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
	delete_draft_ledgers,
	get_voucher_entries,
	upsert_draft_ledger_entries,
)
from erpnext.stock.serial_batch_bundle import (
	SerialBatchCreation,
	combine_datetime,
	get_batch,
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


def get_ledger_warehouse(child_row):
	if child_row.get("is_rejected"):
		return child_row.get("rejected_warehouse")

	return child_row.get("warehouse") or child_row.get("s_warehouse") or child_row.get("t_warehouse")


@frappe.whitelist()
def get_ledger_entries(
	voucher_type: str,
	voucher_no: str,
	voucher_detail_no: str,
	warehouse: str | None = None,
	start: int = 0,
	page_length: int = 50,
	search: str | None = None,
):
	frappe.has_permission(voucher_type, "read", doc=voucher_no, throw=True)
	if not warehouse:
		return frappe._dict({"total_count": 0, "total_qty": 0, "entries": []})

	page_length = min(cint(page_length) or 50, 500)

	table = frappe.qb.DocType("Stock Location Ledger")
	query = (
		frappe.qb.from_(table)
		.select(table.name, table.serial_no, table.batch_no, table.rack, table.bin, table.qty)
		.where(
			(table.voucher_type == voucher_type)
			& (table.voucher_no == voucher_no)
			& (table.voucher_detail_no == voucher_detail_no)
			& (table.warehouse == warehouse)
			& (table.docstatus < 2)
		)
		.orderby(table.idx)
		.limit(page_length)
		.offset(cint(start))
	)

	if search:
		search_term = f"%{search}%"
		query = query.where((table.serial_no.like(search_term)) | (table.batch_no.like(search_term)))

	entries = query.run(as_dict=True)
	for entry in entries:
		entry.qty = abs(flt(entry.qty))

	summary = get_ledger_summary(voucher_type, voucher_no, voucher_detail_no, warehouse)
	summary["entries"] = entries

	return summary


def get_ledger_summary(voucher_type, voucher_no, voucher_detail_no, warehouse):
	table = frappe.qb.DocType("Stock Location Ledger")
	row = (
		frappe.qb.from_(table)
		.select(Count(table.name).as_("total_count"), Sum(table.qty).as_("total_qty"))
		.where(
			(table.voucher_type == voucher_type)
			& (table.voucher_no == voucher_no)
			& (table.voucher_detail_no == voucher_detail_no)
			& (table.warehouse == warehouse)
			& (table.docstatus < 2)
		)
	).run(as_dict=True)[0]

	return frappe._dict(
		{
			"total_count": cint(row.total_count),
			"total_qty": abs(flt(row.total_qty)),
		}
	)


@frappe.whitelist()
def get_amended_ledger_entries(
	voucher_type: str,
	amended_from: str,
	child_doctype: str,
	idx: int,
	warehouse: str | None = None,
):
	"""Composition of the cancelled document a new amendment was made from - the amended child
	rows have fresh names, so the original row is resolved by idx. Used by the inline editor to
	prefill its pending rows; nothing is written until the amended document is saved."""
	frappe.has_permission(voucher_type, "read", doc=amended_from, throw=True)

	detail_name = frappe.db.get_value(
		child_doctype, {"parent": amended_from, "parenttype": voucher_type, "idx": cint(idx)}, "name"
	)
	if not detail_name:
		return []

	filters = {
		"voucher_type": voucher_type,
		"voucher_no": amended_from,
		"voucher_detail_no": detail_name,
		"docstatus": 2,
	}
	if warehouse:
		filters["warehouse"] = warehouse
	# A Stock Reconciliation's cancelled rows include the machine-made reversal leg - only the
	# user-entered new-state leg is a sensible prefill.
	if voucher_type == "Stock Reconciliation":
		filters["is_outward"] = 0

	entries = frappe.get_all(
		"Stock Location Ledger",
		filters=filters,
		fields=["serial_no", "batch_no", "rack", "bin", "qty"],
		order_by="idx, creation",
	)
	for entry in entries:
		entry["qty"] = abs(flt(entry["qty"]))

	return entries


@frappe.whitelist()
def download_ledger_entries_csv(voucher_type: str, voucher_no: str, voucher_detail_no: str, warehouse: str):
	from frappe.utils.csvutils import build_csv_response

	frappe.has_permission(voucher_type, "read", doc=voucher_no, throw=True)
	item_code = frappe.db.get_value(
		"Stock Location Ledger",
		{"voucher_type": voucher_type, "voucher_no": voucher_no, "voucher_detail_no": voucher_detail_no},
		"item_code",
	)
	item = frappe.get_cached_value("Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=True)

	entries = get_voucher_entries(voucher_type, voucher_no, voucher_detail_no, warehouse)

	rows = [get_csv_columns(item)]
	for entry in entries:
		if item.has_serial_no and item.has_batch_no:
			rows.append([entry.serial_no, entry.batch_no, abs(flt(entry.qty))])
		elif item.has_batch_no:
			rows.append([entry.batch_no, abs(flt(entry.qty))])
		else:
			rows.append([entry.serial_no])

	build_csv_response(rows, f"{voucher_detail_no}-entries")


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
	frappe.has_permission(doc.get("doctype"), "write", throw=True)

	voucher_type = doc.get("doctype")
	voucher_no = doc.get("name")
	voucher_detail_no = child_row.get("name")
	warehouse = get_ledger_warehouse(child_row)
	if not warehouse:
		frappe.throw(_("Please set the Warehouse on the row before adding entries"))

	final_rows = merge_ledger_entries(
		voucher_type, voucher_no, voucher_detail_no, warehouse, entries, deleted, cint(replace)
	)

	if not final_rows:
		delete_draft_ledgers(voucher_type, voucher_no, voucher_detail_no, warehouse)
		return frappe._dict({"has_entries": False, "total_count": 0, "total_qty": 0})

	type_of_transaction = get_type_of_transaction(doc, child_row)
	item_code = child_row.get("rm_item_code") or child_row.get("item_code")

	if type_of_transaction == "Inward":
		make_serial_nos(item_code, final_rows)
		make_batch_nos(item_code, final_rows)
		fill_shared_batch_for_serial_only_rows(item_code, final_rows)

	serial_nos = [row["serial_no"] for row in final_rows if row.get("serial_no")]
	batches = frappe._dict()
	for row in final_rows:
		if row.get("batch_no"):
			batches[row["batch_no"]] = flt(batches.get(row["batch_no"])) + (flt(row.get("qty")) or 1.0)

	total_qty = sum(flt(row.get("qty")) or 1.0 for row in final_rows)
	sign = 1 if type_of_transaction == "Inward" else -1

	item = frappe.get_cached_value("Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=True)
	# The serial_nos/batches aggregates collapse rows sharing a batch, losing the physical
	# spot - rack/bin compositions (and plain items, which have neither aggregate) must keep
	# per-row granularity.
	use_explicit_rows = not (item.has_serial_no or item.has_batch_no) or any(
		row.get("rack") or row.get("bin") for row in final_rows
	)

	SerialBatchCreation(
		{
			"item_code": item_code,
			"warehouse": warehouse,
			"posting_datetime": combine_datetime(
				doc.get("posting_date") or today(), doc.get("posting_time") or nowtime()
			),
			"voucher_type": voucher_type,
			"voucher_no": voucher_no,
			"voucher_detail_no": voucher_detail_no,
			"qty": total_qty * sign,
			"type_of_transaction": type_of_transaction,
			"company": doc.get("company"),
			"is_rejected": cint(child_row.get("is_rejected")),
		}
	).make_location_ledger_entries(
		serial_nos=serial_nos or None,
		batch_nos=batches or None,
		rows=final_rows if use_explicit_rows else None,
	)

	return get_ledger_summary(voucher_type, voucher_no, voucher_detail_no, warehouse)


def fill_shared_batch_for_serial_only_rows(item_code, rows):
	"""Manual entry may give only serial numbers for a serial+batch item, leaving batch_no
	blank - mint one shared batch for the whole set instead of leaving it unbatched."""
	if not frappe.get_cached_value("Item", item_code, "has_batch_no"):
		return

	if not any(row.get("serial_no") for row in rows) or any(row.get("batch_no") for row in rows):
		return

	batch_no = get_batch(item_code)
	for row in rows:
		row["batch_no"] = batch_no


def merge_ledger_entries(voucher_type, voucher_no, voucher_detail_no, warehouse, entries, deleted, replace):
	"""Applies the same add/update/delete semantics the grid UI expects, against plain
	Stock Location Ledger draft rows."""
	existing = get_voucher_entries(
		voucher_type,
		voucher_no,
		voucher_detail_no,
		warehouse,
		fields=["name", "serial_no", "batch_no", "rack", "bin", "qty"],
	)
	for row in existing:
		row["qty"] = abs(flt(row.get("qty")))

	if replace:
		return [{key: value for key, value in row.items() if key != "name"} for row in entries]

	rows_by_name = {row["name"]: row for row in existing if row.get("name")}
	if deleted:
		rows_by_name = {name: row for name, row in rows_by_name.items() if name not in deleted}

	for row in entries:
		name = row.get("name")
		if name and name in rows_by_name:
			target = rows_by_name[name]
			if row.get("qty") is not None:
				target["qty"] = flt(row.get("qty")) or 1.0
			for field in ("serial_no", "batch_no", "rack", "bin"):
				if row.get(field):
					target[field] = row.get(field)
		else:
			rows_by_name[f"new-{len(rows_by_name)}-{row.get('serial_no') or row.get('batch_no')}"] = dict(row)

	return list(rows_by_name.values())


def validate_parent_document(child_row, doc):
	if doc.get("doctype") not in SUPPORTED_VOUCHER_TYPES:
		frappe.throw(
			_("{0} is not supported for the inline Serial / Batch editor").format(doc.get("doctype"))
		)

	if child_row.get("parenttype") != doc.get("doctype"):
		frappe.throw(_("The selected row does not belong to the {0}").format(doc.get("doctype")))

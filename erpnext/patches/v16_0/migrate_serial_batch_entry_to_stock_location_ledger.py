import frappe
from frappe.query_builder.functions import Coalesce, Max
from frappe.utils import add_days
from pypika import analytics as an
from pypika.terms import ExistsCriterion

from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import repost_location_balance

COPY_CHUNK_SIZE = 100_000

SLL_COLUMNS = (
	"name",
	"creation",
	"modified",
	"modified_by",
	"owner",
	"docstatus",
	"idx",
	"item_code",
	"serial_no",
	"batch_no",
	"warehouse",
	"company",
	"qty",
	"incoming_rate",
	"outgoing_rate",
	"stock_value_difference",
	"is_outward",
	"reference_for_reservation",
	"voucher_type",
	"voucher_no",
	"voucher_detail_no",
	"posting_datetime",
	"type_of_transaction",
)


def get_source_columns(entry, bundle):
	return (
		entry.name,
		entry.creation,
		entry.modified,
		entry.modified_by,
		entry.owner,
		bundle.docstatus,
		entry.idx,
		Coalesce(entry.item_code, bundle.item_code),
		entry.serial_no,
		entry.batch_no,
		Coalesce(entry.warehouse, bundle.warehouse),
		bundle.company,
		entry.qty,
		entry.incoming_rate,
		entry.outgoing_rate,
		entry.stock_value_difference,
		entry.is_outward,
		entry.reference_for_reservation,
		Coalesce(entry.voucher_type, bundle.voucher_type),
		Coalesce(entry.voucher_no, bundle.voucher_no),
		Coalesce(entry.voucher_detail_no, bundle.voucher_detail_no),
		Coalesce(entry.posting_datetime, bundle.posting_datetime),
		Coalesce(entry.type_of_transaction, bundle.type_of_transaction),
	)


def execute():
	if frappe.db.table_exists("Serial and Batch Entry"):
		copy_bundle_entries_to_location_ledger()

	snapshot_legacy_batch_balances()
	set_running_balances()
	repost_exception_keys()


def copy_bundle_entries_to_location_ledger():
	"""Copy bundle entries in primary-key chunks, entirely inside the database. Duplicate keys
	are skipped, so a killed migrate resumes from wherever it stopped simply by re-running."""
	last_name = ""
	while boundary := get_copy_boundary(last_name):
		insert_entry_chunk(last_name, boundary)
		last_name = boundary


def get_copy_boundary(after_name):
	entry = frappe.qb.DocType("Serial and Batch Entry")
	full_chunk = (
		frappe.qb.from_(entry)
		.select(entry.name)
		.where(entry.name > after_name)
		.orderby(entry.name)
		.limit(1)
		.offset(COPY_CHUNK_SIZE - 1)
		.run(pluck=True)
	)
	if full_chunk:
		return full_chunk[0]

	rows = frappe.qb.from_(entry).select(Max(entry.name)).where(entry.name > after_name).run(pluck=True)
	return rows[0] if rows else None


def insert_entry_chunk(after_name, upto_name):
	entry = frappe.qb.DocType("Serial and Batch Entry")
	bundle = frappe.qb.DocType("Serial and Batch Bundle")
	sll = frappe.qb.DocType("Stock Location Ledger")

	query = (
		frappe.qb.into(sll)
		.columns(*SLL_COLUMNS)
		.from_(entry)
		.inner_join(bundle)
		.on(entry.parent == bundle.name)
		.select(*get_source_columns(entry, bundle))
		.where(
			(bundle.docstatus < 2)
			& (Coalesce(entry.is_cancelled, 0) == 0)
			& (entry.name > after_name)
			& (entry.name <= upto_name)
		)
	)
	query = query.ignore() if frappe.db.db_type == "mariadb" else query.on_conflict().do_nothing()
	query.run()


def snapshot_legacy_batch_balances():
	"""Pre-bundle (v13/v14-era) batch history exists only as batch_no text on Stock Ledger
	Entry, invisible to every Stock Location Ledger reader. Freeze it per company into a
	Stock Closing Balance snapshot: valuation and availability seed their opening balances
	from it, and the frozen period rejects new postings."""
	from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
		reset_stock_closing_cache,
	)

	for company, cutover_date in get_legacy_batch_cutovers().items():
		create_system_stock_closing(company, cutover_date)

	reset_stock_closing_cache()


def get_legacy_batch_cutovers() -> dict:
	sle = frappe.qb.DocType("Stock Ledger Entry")
	sll = frappe.qb.DocType("Stock Location Ledger")

	location_rows = (
		frappe.qb.from_(sll)
		.select(sll.name)
		.where(
			(sll.voucher_type == sle.voucher_type)
			& (sll.voucher_no == sle.voucher_no)
			& (sll.item_code == sle.item_code)
			& (sll.warehouse == sle.warehouse)
			& (sll.batch_no == sle.batch_no)
		)
	)

	rows = (
		frappe.qb.from_(sle)
		.select(sle.company, Max(sle.posting_date).as_("cutover_date"))
		.where(
			(sle.docstatus == 1)
			& (sle.is_cancelled == 0)
			& (sle.batch_no.isnotnull())
			& (sle.batch_no != "")
			& ExistsCriterion(location_rows).negate()
		)
		.groupby(sle.company)
	).run(as_dict=True)

	return {row.company: row.cutover_date for row in rows}


def create_system_stock_closing(company, cutover_date):
	existing = frappe.db.get_value(
		"Stock Closing Entry",
		{"company": company, "docstatus": 1, "to_date": (">=", cutover_date)},
		["name", "status"],
		as_dict=True,
	)

	if existing and existing.status == "Completed":
		return

	if existing:
		doc = frappe.get_doc("Stock Closing Entry", existing.name)
		doc.remove_stock_closing()
	else:
		last_closing = frappe.get_all(
			"Stock Closing Entry",
			fields=["to_date"],
			filters={"company": company, "docstatus": 1},
			order_by="to_date desc",
			limit=1,
		)

		doc = frappe.new_doc("Stock Closing Entry")
		doc.company = company
		doc.from_date = add_days(last_closing[0].to_date, 1) if last_closing else "1900-01-01"
		doc.to_date = cutover_date
		doc.flags.ignore_permissions = True
		doc.insert()
		doc.db_set("docstatus", 1)

	doc.db_set("status", "In Progress")
	doc.create_stock_closing_balance_entries()
	doc.db_set("status", "Completed")


def set_running_balances():
	"""One set-based pass for what repost_location_balance computes row by row: the running
	qty/value per (item, warehouse, serial, batch) key, in the same posting order it uses.
	Keys whose chain SQL cannot express (snapshot-seeded openings, the negative-value clamp)
	are recomputed per key afterwards by repost_exception_keys."""
	sll = frappe.qb.DocType("Stock Location Ledger")
	posting_order = (sll.posting_datetime, sll.creation, sll.idx, sll.name)
	spot_qty = (
		an.Sum(sll.qty)
		.over(sll.item_code, sll.warehouse, sll.serial_no, sll.batch_no, sll.rack, sll.bin)
		.orderby(*posting_order)
	)
	key_value = (
		an.Sum(sll.stock_value_difference)
		.over(sll.item_code, sll.warehouse, sll.serial_no, sll.batch_no)
		.orderby(*posting_order)
	)
	computed = (
		frappe.qb.from_(sll)
		.select(sll.name, spot_qty.as_("qty_after"), key_value.as_("value_after"))
		.where((sll.docstatus == 1) & (Coalesce(sll.voucher_type, "") != "Pick List"))
		.as_("computed")
	)

	(
		frappe.qb.update(sll)
		.join(computed)
		.on(computed.name == sll.name)
		.set(sll.qty_after_transaction, computed.qty_after)
		.set(sll.stock_value, computed.value_after)
		.run()
	)


def repost_exception_keys():
	for item_code, warehouse, serial_no, batch_no in get_snapshot_seeded_keys() | get_clamp_candidate_keys():
		repost_location_balance(
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"serial_no": serial_no,
				"batch_no": batch_no,
			}
		)


def get_snapshot_seeded_keys() -> set:
	if not frappe.db.table_exists("Stock Closing Balance"):
		return set()

	rows = frappe.get_all(
		"Stock Closing Balance",
		filters={"batch_no": ("is", "set")},
		fields=["item_code", "warehouse", "batch_no"],
		distinct=True,
	)
	return {(row.item_code, row.warehouse, None, row.batch_no) for row in rows}


def get_clamp_candidate_keys() -> set:
	rows = frappe.get_all(
		"Stock Location Ledger",
		filters={"docstatus": 1, "stock_value": ("<", 0)},
		fields=["item_code", "warehouse", "serial_no", "batch_no"],
		distinct=True,
	)
	return {(row.item_code, row.warehouse, row.serial_no, row.batch_no) for row in rows}

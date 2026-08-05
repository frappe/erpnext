# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.query_builder import Order
from frappe.utils import cint, flt, format_datetime, get_link_to_form, getdate, now, parse_json

LOCATION_KEY_FIELDS = ("item_code", "warehouse", "serial_no", "batch_no")

SLL_INSERT_FIELDS = (
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
	"rack",
	"bin",
	"warehouse",
	"company",
	"qty",
	"incoming_rate",
	"outgoing_rate",
	"stock_value_difference",
	"is_outward",
	"voucher_type",
	"voucher_no",
	"voucher_detail_no",
	"posting_datetime",
	"type_of_transaction",
)


class StockLocationLedger(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("Stock Location Ledger", ["voucher_no", "voucher_type", "voucher_detail_no"])
	frappe.db.add_index(
		"Stock Location Ledger",
		["item_code", "warehouse", "serial_no", "batch_no", "posting_datetime"],
	)


def make_stock_location_ledgers_from_sle(sle, allow_negative_stock=False, via_landed_cost_voucher=False):
	from erpnext.stock.utils import get_combine_datetime

	validate_not_closed(sle)

	# A consolidated Sales Invoice replays a full day of already-validated POS documents at
	# one posting time - a sell/return/resell sequence dips negative mid-replay even though
	# the net is fine, so per-key negative enforcement must not reject it.
	if sle.get("voucher_type") == "Sales Invoice" and frappe.get_cached_value(
		"Sales Invoice", sle.get("voucher_no"), "is_consolidated"
	):
		allow_negative_stock = True

	if cint(sle.get("is_cancelled")):
		if not frappe.flags.through_repost_item_valuation and not via_landed_cost_voucher:
			validate_ledger_cancellation(sle)
		cancel_stock_location_ledgers(
			sle.get("voucher_type"),
			sle.get("voucher_no"),
			allow_negative_stock=allow_negative_stock,
			via_landed_cost_voucher=via_landed_cost_voucher,
		)
		return

	# A Stock Reconciliation posts its reversal leg and its new-state leg as two SLEs sharing one
	# voucher tuple, so each SLE must find, reconcile and promote only the leg matching its own
	# direction - otherwise the first SLE promotes both and the second finds no drafts left and
	# re-creates rows that already exist.
	is_outward = 1 if flt(sle.get("actual_qty")) < 0 else 0

	if draft_ledgers_exist(sle, is_outward):
		reconcile_draft_ledgers(sle)
		# validate_ledger_promotion already ran earlier, from post_process() during sle.submit(),
		# before set_warehouse_and_status_in_serial_nos had a chance to flip serial statuses -
		# see erpnext/stock/serial_batch_bundle.py.
		submit_stock_location_ledgers(
			sle.get("voucher_type"),
			sle.get("voucher_no"),
			sle.get("voucher_detail_no"),
			sle.get("warehouse"),
			sle.get("item_code"),
			allow_negative_stock=allow_negative_stock,
			is_outward=is_outward,
			posting_datetime=sle.get("posting_datetime")
			or get_combine_datetime(sle.get("posting_date"), sle.get("posting_time")),
		)
	else:
		create_stock_location_ledgers(sle, allow_negative_stock=allow_negative_stock)


def validate_not_closed(sle):
	"""A Stock Closing Balance snapshot is the only record of pre-ledger (legacy) history, so
	serial/batch movements dated inside a closed window can neither be posted nor cancelled -
	the snapshot could not be kept consistent with them."""
	from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
		get_last_completed_closing,
		has_completed_stock_closing,
	)
	from erpnext.stock.utils import get_combine_datetime

	if not has_completed_stock_closing():
		return

	closing = get_last_completed_closing(sle.get("company"))
	if not closing:
		return

	posting_datetime = sle.get("posting_datetime") or get_combine_datetime(
		sle.get("posting_date"), sle.get("posting_time")
	)

	if getdate(closing.to_date) >= getdate(posting_datetime):
		frappe.throw(
			_(
				"Cannot post or cancel a serial/batch stock transaction dated on or before {0}, the period is frozen by Stock Closing Entry {1}."
			).format(
				frappe.format(closing.to_date, "Date"),
				get_link_to_form("Stock Closing Entry", closing.name),
			),
			title=_("Stock Closed"),
		)


def validate_ledger_promotion(sle):
	"""Re-validation before promoting SLL entries on voucher submit: duplicate/already-delivered
	serial checks and future-entries checks."""
	if not frappe.get_cached_value("Item", sle.get("item_code"), "has_serial_no"):
		return

	# A consolidated Sales Invoice replays already-validated POS sales (sell, return, resell
	# intra-day); mid-replay serial statuses would fail these checks spuriously.
	if sle.get("voucher_type") == "Sales Invoice" and frappe.get_cached_value(
		"Sales Invoice", sle.get("voucher_no"), "is_consolidated"
	):
		return

	entries = get_serial_batch_details(sle)
	serial_nos = [entry.serial_no for entry in entries if entry.get("serial_no")]
	if not serial_nos:
		return

	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	is_outward = 1 if flt(sle.get("actual_qty")) < 0 else 0
	creation = SerialBatchCreation(
		{
			"item_code": sle.get("item_code"),
			"warehouse": sle.get("warehouse"),
			"posting_datetime": sle.get("posting_datetime"),
			"voucher_type": sle.get("voucher_type"),
			"voucher_no": sle.get("voucher_no"),
			"voucher_detail_no": sle.get("voucher_detail_no"),
			"company": sle.get("company"),
			"type_of_transaction": "Outward" if is_outward else "Inward",
		}
	)
	resolved_entries = creation.resolve_entries(serial_nos=serial_nos)
	creation.validate_serial_nos_duplicate(resolved_entries)
	creation.validate_existing_serial_nos(resolved_entries)
	creation.check_future_entries_exists(resolved_entries)


def validate_ledger_cancellation(sle):
	"""Blocks cancelling a voucher whose serial/batch entries appear in later transactions -
	the SLL-native port of the bundle-era cancel-time check_future_entries_exists call."""
	item_details = frappe.get_cached_value(
		"Item", sle.get("item_code"), ["has_serial_no", "has_batch_no"], as_dict=True
	)
	if not item_details or not (item_details.has_serial_no or item_details.has_batch_no):
		return

	entries = get_voucher_entries(
		sle.get("voucher_type"),
		sle.get("voucher_no"),
		sle.get("voucher_detail_no"),
		sle.get("warehouse"),
		fields=["serial_no", "batch_no"],
	)
	if not entries:
		return

	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	is_outward = 1 if flt(sle.get("actual_qty")) < 0 else 0
	creation = SerialBatchCreation(
		{
			"item_code": sle.get("item_code"),
			"warehouse": sle.get("warehouse"),
			"posting_datetime": sle.get("posting_datetime"),
			"voucher_type": sle.get("voucher_type"),
			"voucher_no": sle.get("voucher_no"),
			"voucher_detail_no": sle.get("voucher_detail_no"),
			"company": sle.get("company"),
			"type_of_transaction": "Outward" if is_outward else "Inward",
			"via_landed_cost_voucher": sle.get("via_landed_cost_voucher"),
		}
	)
	creation.check_future_entries_exists(entries, is_cancelled=True)


def draft_ledgers_exist(sle, is_outward=None):
	# A packed voucher can have multiple items sharing the same voucher_detail_no/warehouse
	# (the parent row's identifier), so item_code must discriminate here too.
	filters = {
		"voucher_type": sle.get("voucher_type"),
		"voucher_no": sle.get("voucher_no"),
		"voucher_detail_no": sle.get("voucher_detail_no"),
		"warehouse": sle.get("warehouse"),
		"item_code": sle.get("item_code"),
		"docstatus": 0,
	}
	if is_outward is not None:
		filters["is_outward"] = cint(is_outward)

	return bool(frappe.db.exists("Stock Location Ledger", filters))


def drop_stale_ledgers(names):
	"""On the create path (no draft matched this SLE's voucher tuple), a pre-existing row
	sharing a name is stale: an orphaned draft, or a cancelled row left behind by an internal
	cancel+resubmit cycle (e.g. a Landed Cost Voucher repost reuses the same entries, so the
	new insert collides with the entry-derived name of the row it just cancelled). Drop it so
	ignore_duplicates does not
	skip the fresh insert; a currently-submitted (docstatus=1) row is left alone, since that
	would indicate a genuine duplicate submission rather than a stale leftover."""
	if names:
		frappe.db.delete("Stock Location Ledger", {"name": ("in", names), "docstatus": ("in", [0, 2])})


def create_stock_location_ledgers(sle, allow_negative_stock=False):
	entries = get_serial_batch_details(sle)
	if not entries:
		return

	values = [build_location_values(sle, entry, idx=i) for i, entry in enumerate(entries, start=1)]
	drop_stale_ledgers([value[0] for value in values])
	frappe.db.bulk_insert("Stock Location Ledger", list(SLL_INSERT_FIELDS), values, ignore_duplicates=True)

	seen = {}
	for e in entries:
		key = frappe._dict(
			{
				"item_code": sle.get("item_code"),
				"warehouse": sle.get("warehouse"),
				"serial_no": e.get("serial_no"),
				"batch_no": e.get("batch_no"),
			}
		)
		seen[(key.item_code, key.warehouse, key.serial_no, key.batch_no)] = key

	for key in seen.values():
		repost_location_balance(key)

	validate_no_negative_balance(list(seen.values()), allow_negative_stock=allow_negative_stock)


def delete_non_submitted_ledgers_for_voucher(voucher_type, voucher_no):
	"""Frappe blocks deleting a voucher that a non-cancelled Stock Location Ledger row still
	points to (voucher_no is a Dynamic Link). A submitted (docstatus=1) row is a real stock
	movement and should keep blocking deletion, but a draft row left behind by a promotion
	that never completed carries no stock effect and would otherwise wedge the voucher
	permanently. Called from on_trash, before that link check runs."""
	frappe.db.delete(
		"Stock Location Ledger",
		{"voucher_type": voucher_type, "voucher_no": voucher_no, "docstatus": ("in", [0, 2])},
	)


def delete_draft_ledgers(
	voucher_type, voucher_no, voucher_detail_no, warehouse, is_outward=None, item_code=None
):
	filters = {
		"voucher_type": voucher_type,
		"voucher_no": voucher_no,
		"voucher_detail_no": voucher_detail_no,
		"warehouse": warehouse,
		"docstatus": 0,
	}
	# Stock Reconciliation keeps a "current" (is_outward=1) and "new" (is_outward=0) leg alive
	# side by side under the same voucher_detail_no - refreshing one must not delete the other.
	if is_outward is not None:
		filters["is_outward"] = cint(is_outward)
	# Packed items share the parent line's voucher_detail_no, so refreshing one item's drafts
	# must not delete a sibling's.
	if item_code:
		filters["item_code"] = item_code

	frappe.db.delete("Stock Location Ledger", filters)


def upsert_draft_ledger_entries(
	entries,
	voucher_type,
	voucher_no,
	voucher_detail_no,
	warehouse,
	item_code,
	company=None,
	posting_datetime=None,
	is_outward=None,
):
	"""Creates/updates draft Stock Location Ledger rows directly: persists
	the given (serial_no/batch_no/qty) composition as draft (docstatus=0) Stock Location Ledger
	rows, keyed by the voucher tuple, with no bundle document involved at any point. Rate fields
	are left at whatever the caller supplies (usually 0/unset) - the existing valuation pass at
	SLE submission time corrects them regardless of how the row was seeded, exactly as it already
	does for bundle-sourced entries. Pass is_outward when this voucher_detail_no can carry two
	coexisting legs (Stock Reconciliation's current vs new state) so refreshing one leaves the
	other alone."""
	if not voucher_no or not voucher_detail_no:
		return

	delete_draft_ledgers(
		voucher_type, voucher_no, voucher_detail_no, warehouse, is_outward=is_outward, item_code=item_code
	)
	if not entries:
		return

	sle = frappe._dict(
		{
			"item_code": item_code,
			"warehouse": warehouse,
			"company": company,
			"voucher_type": voucher_type,
			"voucher_no": voucher_no,
			"voucher_detail_no": voucher_detail_no,
			"posting_datetime": posting_datetime or now(),
		}
	)
	values = [
		build_location_values(sle, normalize_draft_entry(entry), docstatus=0, idx=i)
		for i, entry in enumerate(entries, start=1)
	]
	drop_stale_ledgers([value[0] for value in values])
	frappe.db.bulk_insert("Stock Location Ledger", list(SLL_INSERT_FIELDS), values, ignore_duplicates=True)


def normalize_draft_entry(entry):
	qty = flt(entry.get("qty"))
	is_outward = 1 if qty < 0 else 0
	# Empty strings must become NULL - the running-balance repost and draft matching resolve
	# an empty key part with isnull(), which never matches a stored ''.
	return frappe._dict(
		{
			"serial_no": entry.get("serial_no") or None,
			"batch_no": entry.get("batch_no") or None,
			"rack": entry.get("rack") or None,
			"bin": entry.get("bin") or None,
			"qty": qty,
			"incoming_rate": flt(entry.get("incoming_rate")),
			"outgoing_rate": flt(entry.get("outgoing_rate")),
			"stock_value_difference": flt(entry.get("stock_value_difference")),
			"is_outward": is_outward,
			"type_of_transaction": "Outward" if is_outward else "Inward",
		}
	)


def has_bundled_entries(
	voucher_type,
	voucher_no,
	voucher_detail_no,
	warehouse,
	is_outward=None,
	item_code=None,
	include_cancelled=False,
):
	return bool(
		get_voucher_entries(
			voucher_type,
			voucher_no,
			voucher_detail_no,
			warehouse,
			is_outward=is_outward,
			item_code=item_code,
			include_cancelled=include_cancelled,
		)
	)


def duplicate_location_entries_for_transfer(sle):
	"""SLL-native equivalent of make_bundle_for_material_transfer: for a Stock Entry material
	transfer, the source leg's entries already exist for this voucher_detail_no; the target leg
	shares the same voucher_detail_no but a different warehouse and direction, and needs its own
	copy of the same composition with qty sign flipped."""
	is_outward = 1 if flt(sle.get("actual_qty")) < 0 else 0
	source_entries = get_voucher_entries(
		sle.get("voucher_type"),
		sle.get("voucher_no"),
		sle.get("voucher_detail_no"),
		fields=["serial_no", "batch_no", "qty"],
		is_outward=cint(not is_outward),
	)
	if not source_entries:
		return False

	entries = [
		{
			"serial_no": entry.serial_no,
			"batch_no": entry.batch_no,
			"qty": abs(flt(entry.qty)) * (-1 if is_outward else 1),
		}
		for entry in source_entries
	]
	upsert_draft_ledger_entries(
		entries,
		voucher_type=sle.get("voucher_type"),
		voucher_no=sle.get("voucher_no"),
		voucher_detail_no=sle.get("voucher_detail_no"),
		warehouse=sle.get("warehouse"),
		item_code=sle.get("item_code"),
		company=sle.get("company"),
		posting_datetime=sle.get("posting_datetime"),
	)
	return True


def reconcile_draft_ledgers(sle):
	# A Stock Reconciliation can pre-create drafts for both its reversal and new-state legs
	# under the same voucher tuple, so matching/cleanup here must stay scoped to this SLE's
	# own direction or it risks reconciling (and then discarding) the other leg's draft.
	is_outward = 1 if flt(sle.get("actual_qty")) < 0 else 0
	entries = get_serial_batch_details(sle)
	apply_sle_rates_on_entries(sle, entries)
	matched = set()
	for entry in entries:
		name = get_matching_draft_ledger(sle, entry, is_outward)
		if name:
			update_draft_valuation(name, entry)
			matched.add(name)
		else:
			values = [build_location_values(sle, entry, docstatus=0)]
			frappe.db.bulk_insert(
				"Stock Location Ledger", list(SLL_INSERT_FIELDS), values, ignore_duplicates=True
			)
			matched.add(values[0][0])

	remove_unmatched_draft_ledgers(sle, matched, is_outward)


def apply_sle_rates_on_entries(sle, entries):
	rate_field = "outgoing_rate" if flt(sle.get("actual_qty")) < 0 else "incoming_rate"
	if not flt(sle.get(rate_field)):
		return

	for entry in entries:
		if not flt(entry.get(rate_field)):
			entry[rate_field] = flt(sle.get(rate_field))
		if not flt(entry.get("stock_value_difference")):
			entry["stock_value_difference"] = flt(entry.get("qty")) * flt(entry.get(rate_field))


def get_matching_draft_ledger(sle, entry, is_outward):
	# A packed voucher can have multiple items sharing the same voucher_detail_no/warehouse -
	# item_code must discriminate here too, or two items' entries can be mismatched.
	filters = {
		"voucher_type": sle.get("voucher_type"),
		"voucher_no": sle.get("voucher_no"),
		"voucher_detail_no": sle.get("voucher_detail_no"),
		"warehouse": sle.get("warehouse"),
		"item_code": sle.get("item_code"),
		"docstatus": 0,
		"is_outward": is_outward,
		"serial_no": entry.get("serial_no") or ["is", "not set"],
		"batch_no": entry.get("batch_no") or ["is", "not set"],
		"rack": entry.get("rack") or ["is", "not set"],
		"bin": entry.get("bin") or ["is", "not set"],
	}
	return frappe.db.get_value("Stock Location Ledger", filters, "name")


def update_draft_valuation(name, entry):
	frappe.db.set_value(
		"Stock Location Ledger",
		name,
		{
			"qty": flt(entry.get("qty")),
			"incoming_rate": flt(entry.get("incoming_rate")),
			"outgoing_rate": flt(entry.get("outgoing_rate")),
			"stock_value_difference": flt(entry.get("stock_value_difference")),
			"is_outward": cint(entry.get("is_outward")),
			"type_of_transaction": entry.get("type_of_transaction"),
		},
		update_modified=False,
	)


def get_voucher_child_table(voucher_type):
	parent_child_map = {
		"Asset Capitalization": "Asset Capitalization Stock Item",
		"Asset Repair": "Asset Repair Consumed Item",
		"Quotation": "Packed Item",
		"Stock Entry": "Stock Entry Detail",
	}
	return parent_child_map.get(voucher_type, f"{voucher_type} Item")


def get_return_against(voucher_type, voucher_no):
	if voucher_type not in (
		"Delivery Note",
		"Sales Invoice",
		"Purchase Invoice",
		"Purchase Receipt",
		"POS Invoice",
		"Subcontracting Receipt",
	):
		return None

	voucher_details = frappe.db.get_value(
		voucher_type, voucher_no, ["is_return", "return_against"], as_dict=True
	)
	if voucher_details and voucher_details.is_return and voucher_details.return_against:
		return voucher_details.return_against

	return None


def resolve_bundle_valuation(sle, prev_sle=None, is_outward=None):
	"""Resolves incoming rate and qty/amount for a voucher's serial / batch entries:
	corrects each entry's incoming_rate/stock_value_difference in place on the Stock
	Location Ledger rows already created for this voucher (creation now always runs before
	valuation, so this works identically for the current posting and for a later repost), then
	returns the aggregate totals a valuation repost needs plus the updated FIFO stock queue
	(None when no non-batchwise FIFO batch was involved). Qty is never touched here — a repost
	must not rewrite physical quantities."""
	entries = get_voucher_entries(
		sle.get("voucher_type"),
		sle.get("voucher_no"),
		sle.get("voucher_detail_no"),
		sle.get("warehouse"),
		fields=[
			"name",
			"serial_no",
			"batch_no",
			"qty",
			"incoming_rate",
			"stock_value_difference",
		],
		item_code=sle.get("item_code"),
		is_outward=is_outward,
	)
	if not entries:
		return 0.0, 0.0, 0.0, None

	return_against = get_return_against(sle.get("voucher_type"), sle.get("voucher_no"))
	if return_against:
		stock_queue = set_return_entry_valuation(sle, entries, return_against, prev_sle)
	else:
		stock_queue = set_inward_entry_valuation(sle, entries, prev_sle)

	resync_location_balance(sle.get("item_code"), sle.get("warehouse"), entries)

	total_amount, total_qty, avg_rate = summarize_entry_valuation(entries)
	return total_amount, total_qty, avg_rate, stock_queue


def resync_location_balance(item_code, warehouse, entries):
	"""BatchNoValuation prices a batch off the running qty_after_transaction/stock_value
	carried on the most recent prior Stock Location Ledger row for that batch. Those running
	balances are seeded before valuation runs (see make_stock_location_ledgers_from_sle), so
	once valuation corrects an entry's stock_value_difference here, the running balance for
	this entry and everything chronologically after it must be recomputed - otherwise later
	entries would price off a stale (pre-valuation) stock_value."""
	keys = {
		(e.get("serial_no"), e.get("batch_no")) for e in entries if e.get("serial_no") or e.get("batch_no")
	}
	for serial_no, batch_no in keys:
		repost_location_balance(
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"serial_no": serial_no,
				"batch_no": batch_no,
			}
		)


def summarize_entry_valuation(entries):
	total_amount = sum(flt(entry.get("qty")) * flt(entry.get("incoming_rate")) for entry in entries)
	total_qty = sum(flt(entry.get("qty")) for entry in entries)
	avg_rate = total_amount / total_qty if total_qty else 0.0
	return total_amount, total_qty, avg_rate


def set_return_entry_valuation(sle, entries, return_against, prev_sle=None):
	from erpnext.controllers.sales_and_purchase_return import get_warehouses_for_return
	from erpnext.stock.utils import get_valuation_method
	from erpnext.stock.valuation import FIFOValuation

	voucher_type = sle.get("voucher_type")
	field = {
		"Sales Invoice": "sales_invoice_item",
		"Purchase Invoice": "purchase_invoice_item",
		"Delivery Note": "dn_detail",
		"Purchase Receipt": "purchase_receipt_item",
	}.get(voucher_type)

	return_against_detail_no = None
	if field and sle.get("voucher_detail_no"):
		return_against_detail_no = frappe.db.get_value(
			get_voucher_child_table(voucher_type), sle.get("voucher_detail_no"), field
		)

	return_warehouse = None
	if voucher_type in ("Purchase Receipt", "Purchase Invoice"):
		warehouses = get_warehouses_for_return(voucher_type, return_against_detail_no)
		if sle.get("warehouse") in warehouses:
			return_warehouse = sle.get("warehouse")

	original_entries = get_serial_batch_valuation_details(
		voucher_type, return_against, return_against_detail_no, return_warehouse, sle.get("item_code")
	)
	serial_rates = {e.serial_no: e.incoming_rate for e in original_entries if e.serial_no}
	batch_rates = {}
	for e in original_entries:
		if e.batch_no and e.batch_no not in batch_rates:
			batch_rates[e.batch_no] = e.incoming_rate

	if not (serial_rates or batch_rates):
		return set_inward_entry_valuation(sle, entries, None)

	# An outward return (purchase return / debit note) must be valued like any other
	# outward for a batchwise-valuation batch - at the batch's current average rate. The
	# original receipt rate is only correct while the batch still holds stock at that
	# rate; once other receipts changed the average, removing at the original rate strands
	# a residue in the batch value (negative when returning the costlier receipt).
	batchwise_avg_rates = get_batchwise_return_avg_rates(sle, entries)

	has_serial_no = any(entry.get("serial_no") for entry in entries)
	valuation_method = get_valuation_method(sle.get("item_code"), sle.get("company"))

	non_batchwise_batches = []
	stock_queue = []
	if not has_serial_no and valuation_method == "FIFO":
		non_batchwise_batches = frappe.get_all(
			"Batch",
			filters={
				"name": ("in", [e.get("batch_no") for e in entries if e.get("batch_no")]),
				"use_batchwise_valuation": 0,
			},
			pluck="name",
		)
		if non_batchwise_batches and prev_sle and prev_sle.get("stock_queue"):
			stock_queue = parse_json(prev_sle.get("stock_queue"))

	has_queue = False
	for entry in entries:
		if entry.get("serial_no"):
			rate = serial_rates.get(entry.get("serial_no"))
		else:
			batch_no = entry.get("batch_no")
			# a batch emptied before the return has no average - fall back to the original rate
			rate = batchwise_avg_rates.get(batch_no) or batch_rates.get(batch_no)

		entry["incoming_rate"] = flt(rate)
		entry["stock_value_difference"] = flt(entry.get("qty")) * flt(rate)

		if non_batchwise_batches and entry.get("batch_no") in non_batchwise_batches and rate is not None:
			qty = flt(entry.get("qty"))
			if qty > 0:
				stock_queue.append([qty, entry["incoming_rate"]])
			elif qty < 0:
				fifo_state = FIFOValuation(stock_queue)
				fifo_state.remove_stock(qty=abs(qty))
				stock_queue = fifo_state.state
			has_queue = True

	update_ledger_valuation(entries)
	return stock_queue if has_queue else None


def get_batchwise_return_avg_rates(sle, entries):
	from erpnext.stock.serial_batch_bundle import BatchNoValuation
	from erpnext.stock.utils import get_valuation_method

	if flt(sle.get("actual_qty")) >= 0:
		return {}

	batch_entries = {
		entry.get("batch_no"): entry
		for entry in entries
		if entry.get("batch_no") and not entry.get("serial_no")
	}
	if not batch_entries:
		return {}

	if get_valuation_method(sle.get("item_code"), sle.get("company")) == "Moving Average" and cint(
		frappe.get_single_value("Stock Settings", "do_not_use_batchwise_valuation")
	):
		return {}

	batchwise_batches = frappe.get_all(
		"Batch",
		filters={"name": ("in", list(batch_entries)), "use_batchwise_valuation": 1},
		pluck="name",
	)
	if not batchwise_batches:
		return {}

	# scoped to batchwise batches only, so BatchNoValuation's non-batchwise machinery
	# (which rewrites ledger rows) never runs
	valuation = BatchNoValuation(
		sle=frappe._dict(dict(sle, batch_nos={name: batch_entries[name] for name in batchwise_batches}))
	)
	return {name: abs(flt(valuation.batch_avg_rate.get(name))) for name in batchwise_batches}


def set_inward_entry_valuation(sle, entries, prev_sle):
	from erpnext.stock.serial_batch_bundle import is_rejected
	from erpnext.stock.utils import get_valuation_method

	voucher_type = sle.get("voucher_type")
	valuation_method = get_valuation_method(sle.get("item_code"), sle.get("company"))

	valuation_field = "valuation_rate"
	if voucher_type in ("Sales Invoice", "Delivery Note", "Quotation"):
		valuation_field = "incoming_rate"
	if voucher_type == "POS Invoice":
		valuation_field = "rate"

	child_table = get_voucher_child_table(voucher_type)
	if voucher_type == "Subcontracting Receipt":
		if not sle.get("voucher_detail_no"):
			return
		valuation_field = "rate"
		if frappe.db.exists("Subcontracting Receipt Supplied Item", sle.get("voucher_detail_no")):
			child_table = "Subcontracting Receipt Supplied Item"
		else:
			child_table = "Subcontracting Receipt Item"

	rate = None
	if sle.get("voucher_detail_no") and sle.get("voucher_no"):
		rate = frappe.db.get_value(child_table, sle.get("voucher_detail_no"), valuation_field)

	is_packed_item = False
	if rate is None and child_table in ("Delivery Note Item", "Sales Invoice Item"):
		rate = frappe.db.get_value(
			"Packed Item",
			{"parent_detail_docname": sle.get("voucher_detail_no"), "item_code": sle.get("item_code")},
			"incoming_rate",
		)
		if rate is None:
			rate = frappe.db.get_value("Packed Item", sle.get("voucher_detail_no"), "incoming_rate")
		if rate is not None:
			is_packed_item = True

	stock_queue = []
	batches = frappe.get_all(
		"Batch",
		filters={
			"name": ("in", [e.get("batch_no") for e in entries if e.get("batch_no")]),
			"use_batchwise_valuation": 0,
		},
		pluck="name",
	)
	if batches and valuation_method == "FIFO" and prev_sle and prev_sle.get("stock_queue"):
		stock_queue = parse_json(prev_sle.get("stock_queue")) or []

	set_valuation_rate_for_rejected_materials = frappe.db.get_single_value(
		"Buying Settings", "set_valuation_rate_for_rejected_materials"
	)
	rejected_entry = is_rejected(voucher_type, sle.get("voucher_detail_no"), sle.get("warehouse"))
	precision = frappe.get_precision("Stock Location Ledger", "incoming_rate")

	has_queue = False
	for entry in entries:
		fifo_batch_wise_val = not (valuation_method == "FIFO" and entry.get("batch_no") in batches)

		if rejected_entry and not set_valuation_rate_for_rejected_materials:
			entry_rate = 0.0
		elif (
			flt(entry.get("incoming_rate"), precision) == flt(rate, precision)
			and not stock_queue
			and fifo_batch_wise_val
			and entry.get("qty")
			and entry.get("stock_value_difference")
		):
			continue
		else:
			entry_rate = rate

		if is_packed_item and entry.get("incoming_rate"):
			entry_rate = entry.get("incoming_rate")

		entry["incoming_rate"] = flt(entry_rate)
		if entry.get("qty"):
			entry["stock_value_difference"] = flt(entry.get("qty")) * entry["incoming_rate"]

		if (
			valuation_method == "FIFO"
			and entry.get("batch_no") in batches
			and entry["incoming_rate"] is not None
		):
			stock_queue.append([entry.get("qty"), entry["incoming_rate"]])
			has_queue = True

	update_ledger_valuation(entries)
	return stock_queue if has_queue else None


def update_ledger_valuation(entries):
	for entry in entries:
		values = {
			"incoming_rate": flt(entry.get("incoming_rate")),
			"stock_value_difference": flt(entry.get("stock_value_difference")),
		}
		frappe.db.set_value("Stock Location Ledger", entry.get("name"), values, update_modified=False)


def remove_unmatched_draft_ledgers(sle, matched, is_outward):
	# A packed voucher can have multiple items sharing the same voucher_detail_no/warehouse -
	# item_code must discriminate here too, or this can delete a sibling item's still-pending draft.
	filters = {
		"voucher_type": sle.get("voucher_type"),
		"voucher_no": sle.get("voucher_no"),
		"voucher_detail_no": sle.get("voucher_detail_no"),
		"warehouse": sle.get("warehouse"),
		"item_code": sle.get("item_code"),
		"docstatus": 0,
		"is_outward": is_outward,
	}
	if matched:
		filters["name"] = ["not in", list(matched)]

	frappe.db.delete("Stock Location Ledger", filters)


def get_voucher_entries(
	voucher_type,
	voucher_no,
	voucher_detail_no=None,
	warehouse=None,
	fields=None,
	item_code=None,
	is_outward=None,
	include_cancelled=False,
):
	table = frappe.qb.DocType("Stock Location Ledger")
	query = (
		frappe.qb.from_(table)
		.where(
			(table.voucher_type == voucher_type)
			& (table.voucher_no == voucher_no)
			& (table.docstatus <= 2 if include_cancelled else table.docstatus < 2)
		)
		.orderby(table.idx, order=Order.asc)
	)

	if voucher_detail_no:
		query = query.where(table.voucher_detail_no == voucher_detail_no)
	if warehouse:
		query = query.where(table.warehouse == warehouse)
	if item_code:
		query = query.where(table.item_code == item_code)
	# A Stock Reconciliation posts a reversal leg and a new-state leg for the same voucher
	# tuple (differing only by direction), so callers identifying "this leg's own rows" must
	# pass is_outward to discriminate — otherwise the two legs' rows get mixed together.
	if is_outward is not None:
		query = query.where(table.is_outward == cint(is_outward))

	for field in fields or ["name"]:
		query = query.select(table[field])

	return query.run(as_dict=True)


def get_ledgers_from_stock_location_ledger(**kwargs) -> list:
	"""SLL-native sibling of get_ledgers_from_serial_batch_bundle: same kwarg-filtering
	convention (any Stock Location Ledger column, plus posting_datetime as a >= bound),
	sourced from the flat ledger directly."""
	table = frappe.qb.DocType("Stock Location Ledger")

	query = (
		frappe.qb.from_(table)
		.select(
			table.serial_no,
			table.warehouse,
			table.item_code,
			table.batch_no,
			table.qty,
			table.incoming_rate,
			table.voucher_detail_no,
			table.voucher_no,
			table.posting_datetime,
			table.is_outward,
		)
		.where(table.docstatus == 1)
		.orderby(table.posting_datetime)
	)

	valid_columns = (
		"name",
		"item_code",
		"warehouse",
		"voucher_no",
		"company",
		"voucher_detail_no",
		"voucher_type",
		"is_outward",
	)
	for key, val in kwargs.items():
		if val is None or key == "get_subcontracted_item":
			continue
		if not val and isinstance(val, list):
			return []
		if key == "posting_datetime":
			query = query.where(table.posting_datetime >= val)
		elif key in valid_columns:
			query = query.where(table[key].isin(val) if isinstance(val, list) else table[key] == val)

	return query.run(as_dict=True)


def get_voucher_wise_serial_batch_from_sll(**kwargs) -> dict:
	"""SLL-native sibling of get_voucher_wise_serial_batch_from_bundle: groups ledger rows by
	(item_code, warehouse, voucher_no) - or additionally by a subcontracted item code, when
	get_subcontracted_item=(doctype, field_name) is passed - into {serial_nos, batch_nos, item_row}."""
	data = get_ledgers_from_stock_location_ledger(**kwargs)
	if not data:
		return {}

	group_by_voucher = {}
	for row in data:
		key = (row.item_code, row.warehouse, row.voucher_no)
		if kwargs.get("get_subcontracted_item"):
			doctype, field_name = kwargs.get("get_subcontracted_item")
			subcontracted_item_code = frappe.get_cached_value(doctype, row.voucher_detail_no, field_name)
			key = (row.item_code, subcontracted_item_code, row.warehouse, row.voucher_no)

		if key not in group_by_voucher:
			group_by_voucher.setdefault(
				key,
				frappe._dict({"serial_nos": [], "batch_nos": defaultdict(float), "item_row": row}),
			)

		child_row = group_by_voucher[key]
		if row.serial_no:
			child_row["serial_nos"].append(row.serial_no)
			child_row["item_row"].qty = len(child_row["serial_nos"]) * (-1 if row.is_outward else 1)

		if row.batch_no:
			child_row["batch_nos"][row.batch_no] += row.qty

	return group_by_voucher


def get_voucher_serial_batch_qty(voucher_type, voucher_no, voucher_detail_no=None, warehouse=None):
	"""Serial/batch composition (serial_no, batch_no, qty) of a voucher line, read
	independent of docstatus so it is available before the ledger is submitted and after
	it is cancelled. A voucher_no only ever holds one lifecycle state, so no duplication."""
	table = frappe.qb.DocType("Stock Location Ledger")
	query = (
		frappe.qb.from_(table)
		.select(table.serial_no, table.batch_no, table.qty)
		.where((table.voucher_type == voucher_type) & (table.voucher_no == voucher_no))
		.orderby(table.idx, order=Order.asc)
	)
	if voucher_detail_no:
		query = query.where(table.voucher_detail_no == voucher_detail_no)
	if warehouse:
		query = query.where(table.warehouse == warehouse)

	return query.run(as_dict=True)


def get_serial_nos_for_voucher(
	voucher_type, voucher_no, voucher_detail_no=None, warehouse=None, item_code=None, include_cancelled=False
):
	rows = get_voucher_entries(
		voucher_type,
		voucher_no,
		voucher_detail_no,
		warehouse,
		fields=["serial_no"],
		item_code=item_code,
		include_cancelled=include_cancelled,
	)
	return [row.serial_no for row in rows if row.serial_no]


def get_batches_for_voucher(voucher_type, voucher_no, voucher_detail_no=None, warehouse=None):
	rows = get_voucher_entries(
		voucher_type, voucher_no, voucher_detail_no, warehouse, fields=["batch_no", "qty"]
	)
	batches = frappe._dict()
	for row in rows:
		if row.batch_no:
			batches[row.batch_no] = flt(batches.get(row.batch_no)) + flt(row.qty)

	return batches


def get_serial_batch_valuation_details(
	voucher_type, voucher_no, voucher_detail_no=None, warehouse=None, item_code=None, is_outward=None
):
	"""Serial/batch valuation rows shaped like stock_ledger.get_serial_from_sabb
	(serial_no, batch_no, name, qty, incoming_rate), sourced from Stock Location Ledger.
	Scoped by item_code so packed-item vouchers (many items per voucher_detail_no) don't mix."""
	return get_voucher_entries(
		voucher_type,
		voucher_no,
		voucher_detail_no,
		warehouse,
		fields=["serial_no", "batch_no", "name", "qty", "incoming_rate", "stock_value_difference"],
		item_code=item_code,
		is_outward=is_outward,
	)


def get_serial_batch_details(sle):
	# Draft rows are the richer record: a serial+batch item's pre-submit drafts carry the
	# auto-minted serials, while the SLE's own fields hold at most one batch/serial string -
	# rebuilding from the fields here would silently drop the minted serials.
	if entries := get_draft_ledger_entries(sle):
		return entries

	# A rack/bin movement of a plain item still needs a ledger row - the rack/bin qty chain
	# lives only here, so the composition gate covers the physical spot too.
	if sle.get("batch_no") or sle.get("serial_no") or sle.get("rack") or sle.get("bin"):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		is_outward = 1 if flt(sle.get("actual_qty")) < 0 else 0
		# serial_no is multiline text; the ledger needs one row per serial, qty +/-1 each
		serial_nos = get_serial_nos(sle.get("serial_no")) if sle.get("serial_no") else [None]
		per_serial_qty = flt(sle.get("actual_qty")) / len(serial_nos) if serial_nos[0] else None

		return [
			frappe._dict(
				{
					"serial_no": serial_no,
					"batch_no": sle.get("batch_no"),
					"rack": sle.get("rack"),
					"bin": sle.get("bin"),
					"qty": per_serial_qty if serial_no else flt(sle.get("actual_qty")),
					"incoming_rate": flt(sle.get("incoming_rate")),
					"outgoing_rate": flt(sle.get("outgoing_rate")),
					"stock_value_difference": flt(sle.get("stock_value_difference")) / len(serial_nos),
					"is_outward": is_outward,
					"type_of_transaction": "Outward" if is_outward else "Inward",
					"creation": sle.get("creation"),
					"idx": idx,
				}
			)
			for idx, serial_no in enumerate(serial_nos, start=1)
		]

	return get_draft_ledger_entries(sle)


def get_draft_ledger_entries(sle):
	"""Entries already sitting as SLL rows for this voucher tuple with no bundle and no single
	legacy serial_no/batch_no field on the sle itself - the source for SLL-native creation paths
	(upsert_draft_ledger_entries), which never populate either. Reused by reconcile_draft_ledgers
	so those drafts get matched/promoted through the normal flow instead of being deleted as
	unmatched. Scoped to the direction of this SLE, since a Stock Reconciliation keeps both legs
	alive under one voucher tuple and each leg is posted by its own SLE."""
	return get_voucher_entries(
		sle.get("voucher_type"),
		sle.get("voucher_no"),
		sle.get("voucher_detail_no"),
		sle.get("warehouse"),
		is_outward=1 if flt(sle.get("actual_qty")) < 0 else 0,
		fields=[
			"name",
			"idx",
			"creation",
			"serial_no",
			"batch_no",
			"rack",
			"bin",
			"qty",
			"incoming_rate",
			"outgoing_rate",
			"stock_value_difference",
			"is_outward",
			"type_of_transaction",
		],
	)


def build_location_values(sle, entry, docstatus=1, idx=None):
	from erpnext.stock.utils import get_combine_datetime

	timestamp = now()
	creation = entry.get("creation") or timestamp
	posting_datetime = sle.get("posting_datetime") or get_combine_datetime(
		sle.get("posting_date"), sle.get("posting_time")
	)
	name = entry.get("name") or frappe.generate_hash(
		f"{sle.get('voucher_no')}{sle.get('voucher_detail_no')}{entry.get('serial_no')}"
		f"{entry.get('batch_no')}{sle.get('warehouse')}",
		10,
	)

	return (
		name,
		creation,
		timestamp,
		frappe.session.user,
		frappe.session.user,
		docstatus,
		entry.get("idx") or idx or 1,
		sle.get("item_code"),
		entry.get("serial_no") or None,
		entry.get("batch_no") or None,
		entry.get("rack") or sle.get("rack") or None,
		entry.get("bin") or sle.get("bin") or None,
		sle.get("warehouse"),
		sle.get("company"),
		flt(entry.get("qty")),
		flt(entry.get("incoming_rate")),
		flt(entry.get("outgoing_rate")),
		flt(entry.get("stock_value_difference")),
		cint(entry.get("is_outward")),
		sle.get("voucher_type"),
		sle.get("voucher_no"),
		sle.get("voucher_detail_no"),
		posting_datetime,
		entry.get("type_of_transaction"),
	)


def submit_stock_location_ledgers(
	voucher_type,
	voucher_no,
	voucher_detail_no=None,
	warehouse=None,
	item_code=None,
	allow_negative_stock=False,
	is_outward=None,
	posting_datetime=None,
):
	_set_docstatus(
		voucher_type,
		voucher_no,
		0,
		1,
		voucher_detail_no=voucher_detail_no,
		warehouse=warehouse,
		item_code=item_code,
		is_outward=is_outward,
		posting_datetime=posting_datetime,
	)
	keys = repost_qty_after_transaction_for_voucher(
		voucher_type, voucher_no, voucher_detail_no, warehouse, item_code
	)
	validate_no_negative_balance(keys, allow_negative_stock=allow_negative_stock)


def revive_cancelled_ledgers_for_voucher(voucher_type, voucher_no):
	"""Bring a voucher's just-cancelled rows back as drafts for an internal cancel+resubmit
	cycle (Landed Cost Voucher repost): the resubmit leg reuses the same composition, and rows
	composed via the inline editor cannot be rebuilt from the child row's own fields."""
	_set_docstatus(voucher_type, voucher_no, 2, 0)


def cancel_stock_location_ledgers(
	voucher_type, voucher_no, allow_negative_stock=False, via_landed_cost_voucher=False
):
	_set_docstatus(voucher_type, voucher_no, 1, 2)
	keys = repost_qty_after_transaction_for_voucher(voucher_type, voucher_no, include_cancelled=True)
	validate_no_negative_balance(
		keys,
		allow_negative_stock=allow_negative_stock,
		is_cancellation=not (frappe.flags.through_repost_item_valuation or via_landed_cost_voucher),
	)


def _set_docstatus(
	voucher_type,
	voucher_no,
	from_docstatus,
	to_docstatus,
	voucher_detail_no=None,
	warehouse=None,
	item_code=None,
	is_outward=None,
	posting_datetime=None,
):
	table = frappe.qb.DocType("Stock Location Ledger")
	query = (
		frappe.qb.update(table)
		.set(table.docstatus, to_docstatus)
		.set(table.modified, now())
		.set(table.modified_by, frappe.session.user)
		.where(
			(table.voucher_type == voucher_type)
			& (table.voucher_no == voucher_no)
			& (table.docstatus == from_docstatus)
		)
	)

	if posting_datetime:
		query = query.set(table.posting_datetime, posting_datetime)
	if from_docstatus == 0 and to_docstatus == 1:
		# the running-balance chain and the batch valuation reader order same-posting-datetime
		# rows by creation, so a promoted draft (composed much earlier via the inline editor)
		# must be restamped onto the SLE timeline like a fresh-created row
		query = query.set(table.creation, now())
	if voucher_detail_no:
		query = query.where(table.voucher_detail_no == voucher_detail_no)
	if warehouse:
		query = query.where(table.warehouse == warehouse)
	if item_code:
		query = query.where(table.item_code == item_code)
	if is_outward is not None:
		query = query.where(table.is_outward == cint(is_outward))

	query.run()


def repost_qty_after_transaction_for_voucher(
	voucher_type, voucher_no, voucher_detail_no=None, warehouse=None, item_code=None, include_cancelled=False
):
	table = frappe.qb.DocType("Stock Location Ledger")
	condition = (table.voucher_type == voucher_type) & (table.voucher_no == voucher_no)
	if voucher_detail_no:
		condition = condition & (table.voucher_detail_no == voucher_detail_no)
	if warehouse:
		condition = condition & (table.warehouse == warehouse)
	if item_code:
		condition = condition & (table.item_code == item_code)
	if not include_cancelled:
		condition = condition & (table.docstatus != 2)

	rows = frappe.qb.from_(table).select(*LOCATION_KEY_FIELDS).where(condition).run(as_dict=True)

	seen = {}
	for row in rows:
		key = tuple(row.get(field) for field in LOCATION_KEY_FIELDS)
		if key in seen:
			continue
		seen[key] = row
		repost_location_balance(row)

	return list(seen.values())


def validate_no_negative_balance(keys, allow_negative_stock=False, is_cancellation=False):
	"""Single home for serial/batch negative-stock enforcement, replacing the scattered
	bundle-era checks (bundle validate/cancel-time qty checks, the cached Batch.batch_qty
	counter, the Stock Ledger Entry.batch_no window-function scan). repost_location_balance
	already recomputed the *entire* chronological qty_after_transaction chain for each key
	before this runs, so a backdated entry that pushes a later, already-submitted row negative
	is caught here too - no separate future-lookahead bookkeeping needed."""
	if not keys:
		return

	from erpnext.stock.serial_batch_bundle import allow_negative_stock_for_batch, get_serial_no_reservation
	from erpnext.stock.stock_ledger import NegativeStockError, is_negative_stock_allowed

	table = frappe.qb.DocType("Stock Location Ledger")
	precision = cint(frappe.db.get_default("float_precision")) or 2

	for key in keys:
		item_code = key.get("item_code")
		warehouse = key.get("warehouse")
		serial_no = key.get("serial_no")
		batch_no = key.get("batch_no")

		if not (serial_no or batch_no):
			continue

		relaxed = allow_negative_stock or is_negative_stock_allowed(item_code=item_code)
		if batch_no:
			if allow_negative_stock_for_batch(batch_no):
				continue
			if relaxed and not is_cancellation:
				continue
		elif relaxed:
			continue

		from pypika import analytics

		opening_qty = 0.0
		condition = (
			(table.item_code == item_code)
			& (table.warehouse == warehouse)
			& (table.docstatus == 1)
			& (table.voucher_type != "Pick List")
		)
		condition &= table.serial_no == serial_no if serial_no else table.serial_no.isnull()
		condition &= table.batch_no == batch_no if batch_no else table.batch_no.isnull()

		if batch_no and not serial_no:
			from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
				get_closing_balance_for_batch,
			)

			# Rows inside a closing snapshot's window keep their pre-snapshot running balance;
			# only the live chain (seeded from the snapshot) is meaningful here.
			if closing := get_closing_balance_for_batch(item_code, warehouse, batch_no):
				condition &= table.posting_datetime > closing.posting_datetime
				opening_qty = flt(closing.actual_qty)

		# qty_after_transaction carries the per-(rack, bin) spot chain, so the key-level running
		# total is recomputed here - an outward from one spot backed by stock sitting in another
		# (or untagged) spot must not read as negative stock.
		running_total = (
			analytics.Sum(table.qty)
			.over(table.item_code)
			.orderby(table.posting_datetime, table.creation, table.idx, table.name)
		)
		chain = (
			frappe.qb.from_(table)
			.select(
				(running_total + opening_qty).as_("qty_after_transaction"),
				table.posting_datetime,
				table.creation,
				table.voucher_type,
				table.voucher_no,
			)
			.where(condition)
			.as_("chain")
		)
		violation = (
			frappe.qb.from_(chain)
			.select(
				chain.qty_after_transaction,
				chain.posting_datetime,
				chain.voucher_type,
				chain.voucher_no,
			)
			.where(chain.qty_after_transaction < 0)
			.orderby(chain.posting_datetime)
			.orderby(chain.creation)
			.limit(1)
		).run(as_dict=True)

		if not violation:
			continue

		if serial_no and not frappe.db.exists(
			"Stock Location Ledger",
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"serial_no": serial_no,
				"docstatus": 1,
				"qty": (">", 0),
			},
		):
			# A serial no with outward rows but no inward row ever is legacy data - its inward
			# predates the Stock Location Ledger (text-only serial_no fields), so its per-serial
			# balance is unknowable here. Bogus serials are still rejected at entry creation by
			# validate_serial_no_status.
			continue

		deficit = flt(violation[0].qty_after_transaction, precision)
		if not (deficit < 0 and abs(deficit) > 0.0001):
			continue

		message = _("{0} units of {1} {2} needed in {3} on {4} for {5} to complete this transaction.").format(
			abs(deficit),
			_("Batch") if batch_no else _("Serial No"),
			bold(batch_no or serial_no),
			get_link_to_form("Warehouse", warehouse),
			format_datetime(violation[0].posting_datetime),
			get_link_to_form(violation[0].voucher_type, violation[0].voucher_no),
		)

		if serial_no:
			reservation = get_serial_no_reservation(item_code, serial_no, warehouse)
			if reservation:
				message += " " + _("Serial No {0} is reserved for {1} via {2}.").format(
					bold(serial_no),
					reservation.voucher_type,
					get_link_to_form(reservation.voucher_type, reservation.voucher_no),
				)

		frappe.throw(message, NegativeStockError, title=_("Insufficient Stock"))


def repost_location_balance(row):
	"""Recompute qty_after_transaction and stock_value for one location key (item +
	warehouse + serial/batch), carrying the running balance in posting order like Stock
	Ledger Entry. Recomputing the whole key keeps backdated and out-of-order entries
	correct, and keeps BatchNoValuation's previous-row rate lookup accurate.

	A batch key with a Stock Closing Balance snapshot starts from the snapshot's qty/value
	instead of zero - pre-Stock Location Ledger history (legacy text-only entries) lives only
	in that snapshot. Rows dated inside the snapshot window are already absorbed in it and
	are excluded from the chain.
	"""
	from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
		get_closing_balance_for_batch,
	)

	opening = None
	if row.get("batch_no") and not row.get("serial_no"):
		opening = get_closing_balance_for_batch(
			row.get("item_code"), row.get("warehouse"), row.get("batch_no")
		)

	entries = get_location_entries(row, after_datetime=opening.posting_datetime if opening else None)
	# qty_after_transaction is scoped to the physical spot: rows carrying a rack/bin chain
	# per (rack, bin) inside the key, rack/bin-less rows form their own chain. Valuation stays
	# per item + warehouse + serial/batch - one value chain across every row of the key.
	total_qty = flt(opening.actual_qty) if opening else 0.0
	sub_qty = {(None, None): total_qty}
	value_balance = flt(opening.stock_value) if opening else 0.0
	for entry in entries:
		spot = (entry.rack or None, entry.bin or None)
		sub_qty[spot] = flt(sub_qty.get(spot)) + flt(entry.qty)
		total_qty += flt(entry.qty)
		value_balance += flt(entry.stock_value_difference)

		# An outgoing valued above the incoming rate (bad legacy rates) would carry the value
		# below zero while qty is not - floor it so later valuations never price off a negative
		# balance. A negative value with negative qty is legitimate negative stock and is kept.
		if value_balance < 0 and total_qty >= 0:
			value_balance = 0.0

		updates = {}
		if flt(entry.qty_after_transaction) != sub_qty[spot]:
			updates["qty_after_transaction"] = sub_qty[spot]
		if flt(entry.stock_value) != value_balance:
			updates["stock_value"] = value_balance

		if updates:
			frappe.db.set_value("Stock Location Ledger", entry.name, updates, update_modified=False)


def get_location_entries(row, after_datetime=None):
	table = frappe.qb.DocType("Stock Location Ledger")
	# A Pick List row is a reservation, not a stock movement - it must not shift the
	# physical running balance.
	condition = (
		(table.item_code == row.get("item_code"))
		& (table.docstatus == 1)
		& (table.voucher_type != "Pick List")
	)
	for field in ("warehouse", "serial_no", "batch_no"):
		value = row.get(field)
		condition = condition & (table[field] == value if value else table[field].isnull())

	if after_datetime:
		condition = condition & (table.posting_datetime > after_datetime)

	return (
		frappe.qb.from_(table)
		.select(
			table.name,
			table.qty,
			table.qty_after_transaction,
			table.stock_value_difference,
			table.stock_value,
			table.rack,
			table.bin,
		)
		.where(condition)
		.orderby(table.posting_datetime, order=Order.asc)
		.orderby(table.creation, order=Order.asc)
		.orderby(table.idx, order=Order.asc)
		.orderby(table.name, order=Order.asc)
		.run(as_dict=True)
	)

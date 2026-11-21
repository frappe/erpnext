import json

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.utils import flt

from erpnext.stock.utils import get_valuation_method, is_serial_no_wise_valuation_disabled

PAGE_SIZE = 50
RETURN_VOUCHERS = (
	"Purchase Receipt",
	"Purchase Invoice",
	"Delivery Note",
	"Sales Invoice",
	"Subcontracting Receipt",
)
QUEUE_METHODS = ("FIFO", "LIFO")


@frappe.whitelist()
def get_valuation_steps(
	item_code: str, warehouse: str, upto: str | None = None, before: str | None = None
) -> dict:
	frappe.has_permission("Stock Ledger Entry", "read", throw=True)
	frappe.has_permission("Item", "read", doc=item_code, throw=True)
	frappe.has_permission("Warehouse", "read", doc=warehouse, throw=True)

	company = frappe.get_cached_value("Warehouse", warehouse, "company")
	item = get_item_context(item_code, company)
	result = frappe._dict(
		item=item,
		warehouse=warehouse,
		company=company,
		currency=frappe.get_cached_value("Company", company, "default_currency"),
		entries=[],
		opening=None,
		has_earlier=False,
		repost_pending=False,
	)
	if item.unsupported:
		return result

	rows, previous, has_earlier = get_ledger_window(item_code, warehouse, upto, before)
	result.entries = build_entries(rows, previous, item.valuation_method)
	set_return_details(result.entries, item_code, warehouse)
	result.opening = get_balance(previous, item.valuation_method)
	result.has_earlier = has_earlier
	result.repost_pending = is_repost_pending(item_code, warehouse, company)
	return result


def get_item_context(item_code, company):
	item = frappe.get_cached_value(
		"Item", item_code, ["item_name", "stock_uom", "has_batch_no", "has_serial_no"], as_dict=True
	)
	unsupported = None
	if item.has_batch_no:
		unsupported = "batch"
	elif item.has_serial_no and not is_serial_no_wise_valuation_disabled(item_code):
		unsupported = "serial"

	return frappe._dict(
		item_code=item_code,
		item_name=item.item_name,
		stock_uom=item.stock_uom,
		valuation_method=get_valuation_method(item_code, company),
		unsupported=unsupported,
	)


def get_ledger_window(item_code, warehouse, upto, before):
	anchor = get_anchor(upto or before, item_code, warehouse)
	rows = fetch_ledger_rows(item_code, warehouse, anchor, inclusive=not before)
	has_earlier = len(rows) > PAGE_SIZE
	previous = rows[PAGE_SIZE] if has_earlier else None
	rows = list(reversed(rows[:PAGE_SIZE]))
	if before or not rows:
		return rows, previous, has_earlier

	start = get_restart_index(rows, previous)
	if start:
		previous = rows[start - 1]
		rows = rows[start:]
		has_earlier = True

	return rows, previous, has_earlier


def get_anchor(entry, item_code, warehouse):
	if not entry:
		return None

	anchor = frappe.db.get_value(
		"Stock Ledger Entry",
		entry,
		["item_code", "warehouse", "posting_datetime", "creation"],
		as_dict=True,
	)
	if not anchor or anchor.item_code != item_code or anchor.warehouse != warehouse:
		frappe.throw(_("Stock Ledger Entry {0} does not belong to this item and warehouse").format(entry))

	return anchor


def fetch_ledger_rows(item_code, warehouse, anchor, inclusive):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = (
		frappe.qb.from_(sle)
		.select(
			sle.name,
			sle.posting_date,
			sle.posting_time,
			sle.voucher_type,
			sle.voucher_no,
			sle.actual_qty,
			sle.incoming_rate,
			sle.qty_after_transaction,
			sle.valuation_rate,
			sle.stock_value,
			sle.stock_value_difference,
			sle.stock_queue,
			sle.is_adjustment_entry,
		)
		.where((sle.item_code == item_code) & (sle.warehouse == warehouse) & (sle.is_cancelled == 0))
		.orderby(sle.posting_datetime, order=Order.desc)
		.orderby(sle.creation, order=Order.desc)
		.limit(PAGE_SIZE + 1)
	)
	if anchor:
		same_time = sle.posting_datetime == anchor.posting_datetime
		creation = sle.creation <= anchor.creation if inclusive else sle.creation < anchor.creation
		query = query.where((sle.posting_datetime < anchor.posting_datetime) | (same_time & creation))

	return query.run(as_dict=True)


def get_restart_index(rows, previous):
	start = 0
	for index, row in enumerate(rows):
		before = rows[index - 1] if index else previous
		if is_reconciliation(row) or not flt(before.qty_after_transaction if before else 0):
			start = index

	return start


def is_reconciliation(row):
	return row.voucher_type == "Stock Reconciliation" and not row.is_adjustment_entry


def get_balance(row, valuation_method):
	if not row:
		return frappe._dict(qty=0.0, value=0.0, rate=0.0, lots=[])

	return frappe._dict(
		qty=flt(row.qty_after_transaction),
		value=flt(row.stock_value),
		rate=flt(row.valuation_rate),
		lots=parse_lots(row.stock_queue) if valuation_method in QUEUE_METHODS else [],
	)


def parse_lots(stock_queue):
	try:
		queue = json.loads(stock_queue or "[]")
	except ValueError:
		return []

	return [[flt(qty), flt(rate)] for qty, rate in queue if flt(qty)]


def build_entries(rows, previous, valuation_method):
	entries = []
	before = get_balance(previous, valuation_method)
	for row in rows:
		after = get_balance(row, valuation_method)
		entry = build_entry(row, before, after)
		if valuation_method in QUEUE_METHODS:
			entry.update(get_lot_changes(before.lots, after.lots))

		entries.append(entry)
		before = after

	return entries


def build_entry(row, before, after):
	qty = flt(row.actual_qty)
	value_change = flt(row.stock_value_difference)
	return frappe._dict(
		name=row.name,
		posting_date=row.posting_date,
		posting_time=row.posting_time,
		voucher_type=row.voucher_type,
		voucher_no=row.voucher_no,
		kind=get_entry_kind(row),
		qty=qty,
		rate=flt(row.incoming_rate) if qty > 0 else abs(value_change / qty) if qty else 0.0,
		value_change=value_change,
		qty_before=before.qty,
		value_before=before.value,
		rate_before=before.rate,
		qty_after=after.qty,
		value_after=after.value,
		rate_after=after.rate,
		lots_after=after.lots,
	)


def get_entry_kind(row):
	if is_reconciliation(row):
		return "reconciliation"
	if not flt(row.actual_qty):
		return "revaluation"

	return "in" if flt(row.actual_qty) > 0 else "out"


def get_lot_changes(lots_before, lots_after):
	before = sum_lots_by_rate(lots_before)
	after = sum_lots_by_rate(lots_after)
	used = [[flt(qty - after.get(rate, 0)), rate] for rate, qty in before.items() if qty > after.get(rate, 0)]
	added = [
		[flt(qty - before.get(rate, 0)), rate] for rate, qty in after.items() if qty > before.get(rate, 0)
	]
	return {"lots_before": lots_before, "used_lots": used, "added_lots": added}


def sum_lots_by_rate(lots):
	totals = {}
	for qty, rate in lots:
		totals[rate] = flt(totals.get(rate, 0) + qty)

	return totals


def set_return_details(entries, item_code, warehouse):
	returns = {}
	for voucher_type in RETURN_VOUCHERS:
		voucher_nos = {entry.voucher_no for entry in entries if entry.voucher_type == voucher_type}
		if voucher_nos:
			returns.update(get_returns_of_type(voucher_type, voucher_nos))

	if not returns:
		return

	rates = get_original_rates({d.return_against for d in returns.values()}, item_code, warehouse)
	for entry in entries:
		if detail := returns.get(entry.voucher_no):
			entry.is_return = 1
			entry.return_against = detail.return_against
			entry.original_rate = rates.get((detail.return_against, entry.qty < 0))


def get_returns_of_type(voucher_type, voucher_nos):
	doctype = frappe.qb.DocType(voucher_type)
	vouchers = (
		frappe.qb.from_(doctype)
		.select(doctype.name, doctype.return_against)
		.where(doctype.name.isin(list(voucher_nos)) & (doctype.is_return == 1))
		.run(as_dict=True)
	)
	return {voucher.name: voucher for voucher in vouchers if voucher.return_against}


def get_original_rates(voucher_nos, item_code, warehouse):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	rows = (
		frappe.qb.from_(sle)
		.select(sle.voucher_no, sle.actual_qty, sle.incoming_rate, sle.stock_value_difference)
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (sle.is_cancelled == 0)
			& (sle.actual_qty != 0)
			& (sle.voucher_no.isin(list(voucher_nos)))
		)
		.run(as_dict=True)
	)
	return get_weighted_rates(rows)


def get_weighted_rates(rows):
	totals = {}
	for row in rows:
		inward = flt(row.actual_qty) > 0
		qty = abs(flt(row.actual_qty))
		value = qty * flt(row.incoming_rate) if inward else abs(flt(row.stock_value_difference))
		total = totals.setdefault((row.voucher_no, inward), [0.0, 0.0])
		total[0] += qty
		total[1] += value

	return {key: value / qty for key, (qty, value) in totals.items() if qty}


def is_repost_pending(item_code, warehouse, company):
	repost = frappe.qb.DocType("Repost Item Valuation")
	pending = (
		frappe.qb.from_(repost)
		.select(repost.name)
		.where(
			(repost.docstatus == 1)
			& (repost.company == company)
			& (repost.status.isin(["Queued", "In Progress"]))
			& (
				(repost.based_on == "Transaction")
				| ((repost.item_code == item_code) & (repost.warehouse == warehouse))
			)
		)
		.limit(1)
		.run()
	)
	return bool(pending)

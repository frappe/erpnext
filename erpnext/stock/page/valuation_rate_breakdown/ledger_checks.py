import json

import frappe
from frappe.query_builder import Order
from frappe.utils import cint, flt

from erpnext.stock.page.valuation_rate_breakdown.serial_batch import ROUNDING_GAP

QUEUE_METHODS = ("FIFO", "LIFO")
WALK_SIZE = 500


def set_ledger_problems(entries, rows, previous, item):
	precision = get_precision()
	before = previous
	for entry, row in zip(entries, rows, strict=True):
		problems = (
			None if entry.awaiting_recalculation else get_row_problems(row, before, entry, item, precision)
		)
		if problems:
			entry.ledger_problems = problems
		before = row


def get_precision():
	return cint(frappe.db.get_single_value("System Settings", "float_precision")) or 3


def get_row_problems(row, before, entry, item, precision):
	checks = (check_qty, check_value, check_rate, check_lots, check_outgoing_rate)
	problems = []
	for check in checks:
		if problem := check(row, before or frappe._dict(), entry, item, precision):
			problems.append(problem)

	return problems


def check_qty(row, before, entry, item, precision):
	if is_quantity_reset(row):
		return None

	expected = flt(before.qty_after_transaction) + flt(row.actual_qty)
	if flt(expected - flt(row.qty_after_transaction), precision) == 0:
		return None

	return frappe._dict(check="qty", expected=expected, actual=flt(row.qty_after_transaction))


def is_quantity_reset(row):
	return (
		row.voucher_type == "Stock Reconciliation"
		and not row.serial_and_batch_bundle
		and not row.is_adjustment_entry
	)


def check_value(row, before, entry, item, precision):
	expected = flt(before.stock_value) + flt(row.stock_value_difference)
	if abs(expected - flt(row.stock_value)) < ROUNDING_GAP:
		return None

	return frappe._dict(check="value", expected=expected, actual=flt(row.stock_value))


def check_rate(row, before, entry, item, precision):
	expected = flt(row.valuation_rate) * flt(row.qty_after_transaction)
	if abs(expected - flt(row.stock_value)) < ROUNDING_GAP:
		return None

	return frappe._dict(check="rate", expected=expected, actual=flt(row.stock_value))


def check_lots(row, before, entry, item, precision):
	if item.valued_by or item.valuation_method not in QUEUE_METHODS or row.serial_and_batch_bundle:
		return None

	lots = read_lots(row.stock_queue)
	qty = sum(flt(lot_qty) for lot_qty, _rate in lots)
	value = sum(flt(lot_qty) * flt(rate) for lot_qty, rate in lots)
	same_qty = flt(qty - flt(row.qty_after_transaction), precision) == 0
	if same_qty and abs(value - flt(row.stock_value)) < ROUNDING_GAP:
		return None

	return frappe._dict(check="lots", qty=qty, value=value)


def read_lots(stock_queue):
	try:
		return json.loads(stock_queue or "[]")
	except ValueError:
		return []


def check_outgoing_rate(row, before, entry, item, precision):
	qty = flt(row.actual_qty)
	if item.valued_by or item.valuation_method != "Moving Average" or qty >= 0:
		return None
	if entry.is_return or is_quantity_reset(row) or row.is_adjustment_entry:
		return None
	if flt(before.qty_after_transaction) <= 0:
		return None

	expected = flt(before.valuation_rate)
	if abs(qty * expected - flt(row.stock_value_difference)) < ROUNDING_GAP:
		return None

	return frappe._dict(
		check="outgoing_rate", expected=expected, actual=abs(flt(row.stock_value_difference) / qty)
	)


def set_repost_start(entries, rows, previous, item, warehouse):
	first = next((index for index, entry in enumerate(entries) if entry.ledger_problems), None)
	if first is None:
		return

	precision = get_precision()
	start = rows[first]
	if first == 0 and previous and has_state_problem(previous, item, precision):
		start = find_run_start(item, warehouse, previous, precision)

	entries[first].repost_from = frappe._dict(
		name=start.name,
		posting_date=start.posting_date,
		posting_time=start.posting_time,
		voucher_type=start.voucher_type,
		voucher_no=start.voucher_no,
	)


def has_state_problem(row, item, precision):
	empty = frappe._dict()
	return bool(
		check_rate(row, empty, empty, item, precision) or check_lots(row, empty, empty, item, precision)
	)


def find_run_start(item, warehouse, row, precision):
	start = row
	while True:
		older = get_older_rows(item.item_code, warehouse, start)
		for candidate in older:
			if not has_state_problem(candidate, item, precision):
				return start
			start = candidate

		if len(older) < WALK_SIZE:
			return start


def get_older_rows(item_code, warehouse, row):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	same_time = (sle.posting_datetime == row.posting_datetime) & (sle.creation < row.creation)
	return (
		frappe.qb.from_(sle)
		.select(
			sle.name,
			sle.posting_date,
			sle.posting_time,
			sle.voucher_type,
			sle.voucher_no,
			sle.qty_after_transaction,
			sle.valuation_rate,
			sle.stock_value,
			sle.stock_queue,
			sle.serial_and_batch_bundle,
			sle.posting_datetime,
			sle.creation,
		)
		.where((sle.item_code == item_code) & (sle.warehouse == warehouse) & (sle.is_cancelled == 0))
		.where((sle.posting_datetime < row.posting_datetime) | same_time)
		.orderby(sle.posting_datetime, order=Order.desc)
		.orderby(sle.creation, order=Order.desc)
		.limit(WALK_SIZE)
		.run(as_dict=True)
	)

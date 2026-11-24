import json

import frappe
from frappe.query_builder import Order
from frappe.utils import flt

from erpnext.stock.valuation import FIFOValuation, LIFOValuation

REPLAY_LIMIT = 2000
MA_METHOD = "Moving Average"
QUEUE_CLASSES = {"FIFO": FIFOValuation, "LIFO": LIFOValuation}


def set_backdated_details(entries, rows, item_code, warehouse, valuation_method):
	if not rows:
		return

	counts = get_later_dated_counts(rows, item_code, warehouse)
	late_rows = get_late_rows(rows, item_code, warehouse)
	rows_by_name = {row.name: row for row in rows}
	affected = []
	for entry in entries:
		row = rows_by_name[entry.name]
		entry.entered_on = row.creation
		entry.later_dated_count = counts.get(entry.name, 0)
		entry.changed_by = get_changed_by(row, late_rows)
		if entry.changed_by:
			entry.awaiting_recalculation = is_awaiting_recalculation(row, entry.changed_by)
			affected.append((entry, row))

	if affected and can_replay(valuation_method):
		set_rates_when_entered(affected, item_code, warehouse, valuation_method)


def is_awaiting_recalculation(row, changed_by):
	return row.modified < max(change.changed_on for change in changed_by)


def can_replay(valuation_method):
	return valuation_method == MA_METHOD or valuation_method in QUEUE_CLASSES


def get_later_dated_counts(rows, item_code, warehouse):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	later_rows = (
		frappe.qb.from_(sle)
		.select(sle.voucher_no, sle.posting_datetime, sle.creation)
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (sle.posting_datetime > min(row.posting_datetime for row in rows))
			& (sle.creation < max(row.creation for row in rows))
			& (sle.is_cancelled == 0)
		)
		.run(as_dict=True)
	)
	counts = {row.name: count_later_dated(row, later_rows) for row in rows}
	return {name: count for name, count in counts.items() if count}


def count_later_dated(row, later_rows):
	return sum(
		1
		for later in later_rows
		if later.posting_datetime > row.posting_datetime
		and later.creation < row.creation
		and later.voucher_no != row.voucher_no
	)


def get_late_rows(rows, item_code, warehouse):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	first_entered = min(row.creation for row in rows)
	added = late_rows_query(sle, rows, item_code, warehouse).where(
		(sle.creation > first_entered) & (sle.is_cancelled == 0)
	)
	cancelled = late_rows_query(sle, rows, item_code, warehouse).where(
		(sle.is_cancelled == 1) & (sle.modified > first_entered)
	)
	late_rows = added.run(as_dict=True) + cancelled.run(as_dict=True)
	return sorted(late_rows, key=lambda late: (late.posting_datetime, late.creation))


def late_rows_query(sle, rows, item_code, warehouse):
	return (
		frappe.qb.from_(sle)
		.select(
			sle.name,
			sle.voucher_type,
			sle.voucher_no,
			sle.posting_date,
			sle.posting_time,
			sle.posting_datetime,
			sle.creation,
			sle.modified,
			sle.is_cancelled,
		)
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (sle.posting_datetime < max(row.posting_datetime for row in rows))
		)
	)


def get_changed_by(row, late_rows):
	changes = {}
	for late in late_rows:
		if late.voucher_no == row.voucher_no or late.posting_datetime >= row.posting_datetime:
			continue

		kind = get_change_kind(late, row.creation)
		if kind:
			changes.setdefault(
				(late.voucher_type, late.voucher_no, kind),
				frappe._dict(
					voucher_type=late.voucher_type,
					voucher_no=late.voucher_no,
					posting_date=late.posting_date,
					posting_time=late.posting_time,
					posting_datetime=late.posting_datetime,
					kind=kind,
					changed_on=late.modified if kind == "cancelled" else late.creation,
				),
			)

	return list(changes.values())


def get_change_kind(late, entered_on):
	if late.creation > entered_on:
		return None if late.is_cancelled else "added"

	if late.is_cancelled and late.modified > entered_on:
		return "cancelled"

	return None


def set_rates_when_entered(affected, item_code, warehouse, valuation_method):
	earliest = min(change.posting_datetime for entry, _row in affected for change in entry.changed_by)
	start = get_start_row(item_code, warehouse, earliest)
	upto = max(row.posting_datetime for _entry, row in affected)
	if is_too_long_to_replay(item_code, warehouse, start, upto):
		return

	history = get_history(item_code, warehouse, start, upto, valuation_method)
	for entry, row in affected:
		replayed = replay_until(row, start, history, valuation_method, get_return_rate(entry))
		if replayed:
			entry.rate_when_entered = replayed.rate
			entry.rate_after_when_entered = replayed.rate_after


def get_start_row(item_code, warehouse, earliest):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	rows = (
		frappe.qb.from_(sle)
		.select(sle.posting_datetime, sle.creation, sle.qty_after_transaction, sle.valuation_rate)
		.select(sle.stock_value, sle.stock_queue)
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (sle.is_cancelled == 0)
			& (sle.posting_datetime < earliest)
		)
		.orderby(sle.posting_datetime, order=Order.desc)
		.orderby(sle.creation, order=Order.desc)
		.limit(1)
		.run(as_dict=True)
	)
	return rows[0] if rows else None


def is_too_long_to_replay(item_code, warehouse, start, upto):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = history_query(sle, item_code, warehouse, start, upto)
	return bool(query.select(sle.name).limit(1).offset(REPLAY_LIMIT).run())


def get_history(item_code, warehouse, start, upto, valuation_method):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = (
		history_query(sle, item_code, warehouse, start, upto)
		.select(sle.name, sle.voucher_type, sle.voucher_no, sle.posting_datetime, sle.creation, sle.modified)
		.select(sle.is_cancelled, sle.actual_qty, sle.incoming_rate, sle.stock_value_difference)
		.select(sle.qty_after_transaction, sle.valuation_rate, sle.stock_value, sle.is_adjustment_entry)
		.orderby(sle.posting_datetime)
		.orderby(sle.creation)
	)
	if valuation_method in QUEUE_CLASSES:
		query = query.select(sle.stock_queue)

	return query.run(as_dict=True)


def history_query(sle, item_code, warehouse, start, upto):
	query = frappe.qb.from_(sle).where(
		(sle.item_code == item_code) & (sle.warehouse == warehouse) & (sle.posting_datetime <= upto)
	)
	if start:
		query = query.where(
			(sle.posting_datetime > start.posting_datetime)
			| ((sle.posting_datetime == start.posting_datetime) & (sle.creation > start.creation))
		)

	return query


def get_return_rate(entry):
	if entry.is_return and entry.qty < 0 and entry.original_rate:
		return flt(entry.original_rate)

	return None


def replay_until(target, start, history, valuation_method, return_rate=None):
	book = make_book(start, valuation_method)
	for row in history:
		if not existed_when_entered(row, target.creation):
			continue

		if row.name == target.name:
			return book.apply(row, return_rate)

		if row.modified <= target.creation and not row.is_cancelled:
			book.sync(row)
		else:
			book.apply(row)

	return None


def existed_when_entered(row, entered_on):
	if row.creation > entered_on:
		return False

	return not row.is_cancelled or row.modified > entered_on


def make_book(start, valuation_method):
	book = MovingAverageBook() if valuation_method == MA_METHOD else QueueBook(valuation_method)
	if start:
		book.sync(start)

	return book


class MovingAverageBook:
	def __init__(self):
		self.qty = 0.0
		self.rate = 0.0

	def sync(self, row):
		self.qty = flt(row.qty_after_transaction)
		self.rate = flt(row.valuation_rate)

	def apply(self, row, return_rate=None):
		qty = flt(row.actual_qty)
		if is_reconciliation(row):
			self.sync(row)
			return frappe._dict(rate=self.rate, rate_after=self.rate)

		if not qty:
			self.revalue(flt(row.stock_value_difference))
			return frappe._dict(rate=0.0, rate_after=self.rate)

		rate = flt(row.incoming_rate) if qty > 0 else return_rate or self.rate
		if qty > 0:
			self.receive(qty, rate)
		elif return_rate:
			self.return_at(qty, return_rate)
		else:
			self.qty += qty

		return frappe._dict(rate=rate, rate_after=self.rate)

	def receive(self, qty, rate):
		new_qty = self.qty + qty
		if self.qty <= 0 or new_qty <= 0:
			self.rate = rate
		else:
			self.rate = (self.qty * self.rate + qty * rate) / new_qty

		self.qty = new_qty

	def return_at(self, qty, rate):
		new_qty = self.qty + qty
		if new_qty > 0:
			self.rate = (self.qty * self.rate + qty * rate) / new_qty
		elif new_qty == 0 or self.qty >= 0:
			self.rate = rate

		self.qty = new_qty

	def revalue(self, value_change):
		if self.qty:
			self.rate = (self.qty * self.rate + value_change) / self.qty


class QueueBook:
	def __init__(self, valuation_method):
		self.valuation_class = QUEUE_CLASSES[valuation_method]
		self.queue = self.valuation_class([])

	def sync(self, row):
		self.queue = self.valuation_class(load_queue(row.stock_queue))

	def apply(self, row, return_rate=None):
		qty = flt(row.actual_qty)
		if is_reconciliation(row):
			self.queue = self.valuation_class([[flt(row.qty_after_transaction), flt(row.valuation_rate)]])
			return frappe._dict(rate=flt(row.valuation_rate), rate_after=self.rate_after())

		if not qty:
			return frappe._dict(rate=0.0, rate_after=self.rate_after())

		if qty > 0:
			rate = flt(row.incoming_rate)
			self.queue.add_stock(qty, rate)
		else:
			used = self.queue.remove_stock(
				abs(qty), outgoing_rate=return_rate or 0.0, is_return_purchase_entry=bool(return_rate)
			)
			rate = sum(flt(lot_qty) * flt(lot_rate) for lot_qty, lot_rate in used) / abs(qty)

		return frappe._dict(rate=rate, rate_after=self.rate_after())

	def rate_after(self):
		qty = sum(flt(lot_qty) for lot_qty, _rate in self.queue.state)
		value = sum(flt(lot_qty) * flt(lot_rate) for lot_qty, lot_rate in self.queue.state)
		return value / qty if qty else 0.0


def load_queue(stock_queue):
	try:
		queue = json.loads(stock_queue or "[]")
	except ValueError:
		return []

	return [[flt(qty), flt(rate)] for qty, rate in queue]


def is_reconciliation(row):
	return row.voucher_type == "Stock Reconciliation" and not row.is_adjustment_entry

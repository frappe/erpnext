import frappe
from frappe.utils import flt

SERIALS_SHOWN = 10
MISMATCHES_SHOWN = 5
RETURN_DOCTYPES = ("Purchase Receipt", "Purchase Invoice", "Delivery Note", "Sales Invoice")


def set_serial_batch_details(result, entries, rows, focus=None):
	if not rows:
		return

	item = result.item
	history = get_bundle_history(item.item_code, result.warehouse, rows[-1])
	focus_name = focus.name if focus else None
	if item.valued_by == "serial":
		book = SerialBook(focus_name)
	else:
		book = BatchBook(item.item_code, history, focus_name)

	window = {row.name for row in rows}
	for row in history:
		book.add(row, row.sle in window)

	for entry in entries:
		entry.parts = book.entry_parts(entry.name)

	result.stock_parts = book.stock_parts()
	result.stock_gap = get_stock_gap(rows[-1], result.stock_parts, book.mismatches)
	set_labels(entries, result, item.valued_by)


def get_bundle_history(item_code, warehouse, last_row):
	entry = frappe.qb.DocType("Serial and Batch Entry")
	sle = frappe.qb.DocType("Stock Ledger Entry")
	same_time = sle.posting_datetime == last_row.posting_datetime
	return (
		frappe.qb.from_(entry)
		.inner_join(sle)
		.on((sle.serial_and_batch_bundle == entry.parent) & (sle.is_cancelled == 0))
		.select(entry.serial_no, entry.batch_no, entry.qty, entry.stock_value_difference)
		.select(sle.name.as_("sle"), sle.voucher_type, sle.voucher_no, sle.posting_date)
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (
				(sle.posting_datetime < last_row.posting_datetime)
				| (same_time & (sle.creation <= last_row.creation))
			)
			& (entry.docstatus == 1)
			& (entry.is_cancelled == 0)
		)
		.orderby(sle.posting_datetime)
		.orderby(sle.creation)
		.orderby(entry.idx)
		.run(as_dict=True)
	)


def unit_rate(qty, value):
	return abs(flt(value) / flt(qty)) if flt(qty) else 0.0


def is_different(a, b):
	return abs(flt(a) - flt(b)) >= 0.005


class SerialBook:
	def __init__(self, focus=None):
		self.focus = focus
		self.held = {}
		self.parts = {}
		self.mismatches = {}

	def add(self, row, in_window):
		if not row.serial_no:
			return

		qty = flt(row.qty)
		rate = unit_rate(qty, row.stock_value_difference)
		before = self.held.get(row.serial_no)
		source = None
		if qty > 0:
			self.held[row.serial_no] = frappe._dict(rate=rate, row=row)
		else:
			source = self.held.pop(row.serial_no, None)
			if source and is_different(source.rate, rate):
				self.add_mismatch(row, source.rate, rate)

		if in_window and self.focus in (None, row.serial_no):
			group = add_serial_to_group(self.parts.setdefault(row.sle, {}), row, rate, source)
			group.setdefault("qty_before", 1.0 if before else 0.0)
			group.setdefault("value_before", before.rate if before else 0.0)

	def add_mismatch(self, row, expected, actual):
		mismatch = self.mismatches.setdefault(
			row.sle,
			frappe._dict(
				voucher_type=row.voucher_type,
				voucher_no=row.voucher_no,
				posting_date=row.posting_date,
				serial_nos=[],
				expected=expected,
				actual=actual,
				gap=0.0,
			),
		)
		mismatch.serial_nos.append(row.serial_no)
		mismatch.gap += expected - actual

	def entry_parts(self, name):
		return list(self.parts.get(name, {}).values())

	def stock_parts(self):
		groups = {}
		for serial_no, held in self.held.items():
			group = groups.setdefault(
				flt(held.rate, 2), frappe._dict(serial_nos=[], more=0, qty=0.0, value=0.0, rate=held.rate)
			)
			add_serial(group, serial_no, 1, held.rate)

		return sorted(groups.values(), key=lambda group: -group.qty)


def add_serial_to_group(groups, row, rate, source):
	key = (flt(rate, 2), source.row.voucher_no if source else None, flt(source.rate, 2) if source else None)
	group = groups.setdefault(key, frappe._dict(serial_nos=[], more=0, qty=0.0, value=0.0, rate=rate))
	if source:
		group.update(
			source_voucher_type=source.row.voucher_type,
			source_voucher_no=source.row.voucher_no,
			source_date=source.row.posting_date,
			source_rate=source.rate,
		)

	add_serial(group, row.serial_no, flt(row.qty), rate)
	return group


def add_serial(group, serial_no, qty, rate):
	group.qty += qty
	group.value += qty * rate
	if len(group.serial_nos) < SERIALS_SHOWN:
		group.serial_nos.append(serial_no)
	else:
		group.more += 1


class BatchBook:
	def __init__(self, item_code, history, focus=None):
		self.focus = focus
		self.batches = get_batches({row.batch_no for row in history if row.batch_no}, item_code)
		self.balances = {}
		self.parts = {}
		self.mismatches = {}

	def add(self, row, in_window):
		if not row.batch_no:
			return

		balance = self.balances.setdefault(row.batch_no, [0.0, 0.0])
		qty, value = flt(row.qty), flt(row.stock_value_difference)
		if in_window and self.focus in (None, row.batch_no):
			self.add_part(row, balance, qty, value)

		own_rate = self.batches.get(row.batch_no, frappe._dict()).own_rate
		if own_rate and qty < 0 and balance[0] > 0:
			expected = unit_rate(balance[0], balance[1])
			if is_different(expected, unit_rate(qty, value)):
				self.add_mismatch(row, expected, unit_rate(qty, value), qty)

		balance[0] += qty
		balance[1] += value

	def add_part(self, row, balance, qty, value):
		batch = self.batches.get(row.batch_no, frappe._dict())
		part = self.parts.setdefault(row.sle, {}).setdefault(
			row.batch_no,
			frappe._dict(
				batch_no=row.batch_no,
				batch_id=batch.batch_id or row.batch_no,
				own_rate=bool(batch.own_rate),
				qty_before=balance[0],
				value_before=balance[1],
				qty=0.0,
				value=0.0,
			),
		)
		part.qty += qty
		part.value += value

	def add_mismatch(self, row, expected, actual, qty):
		mismatch = self.mismatches.setdefault(
			row.sle,
			frappe._dict(
				voucher_type=row.voucher_type,
				voucher_no=row.voucher_no,
				posting_date=row.posting_date,
				batch_ids=[],
				expected=expected,
				actual=actual,
				gap=0.0,
			),
		)
		mismatch.batch_ids.append(self.batches.get(row.batch_no, frappe._dict()).batch_id or row.batch_no)
		mismatch.gap += (expected - actual) * abs(qty)

	def entry_parts(self, name):
		parts = list(self.parts.get(name, {}).values())
		for part in parts:
			part.rate = unit_rate(part.qty, part.value)
			part.qty_after = part.qty_before + part.qty
			part.value_after = part.value_before + part.value

		return parts

	def stock_parts(self):
		parts, shared = [], frappe._dict(shared=True, count=0, qty=0.0, value=0.0)
		for batch_no, (qty, value) in self.balances.items():
			if not flt(qty, 6) and not is_different(value, 0):
				continue

			batch = self.batches.get(batch_no, frappe._dict())
			if not batch.own_rate:
				shared.update(count=shared.count + 1, qty=shared.qty + qty, value=shared.value + value)
				continue

			label = batch.batch_id or batch_no
			parts.append(frappe._dict(batch_no=batch_no, batch_id=label, qty=qty, value=value))

		parts.sort(key=lambda part: -part.qty)
		if shared.count:
			parts.append(shared)

		for part in parts:
			part.rate = unit_rate(part.qty, part.value)

		return parts


def get_batches(batch_nos, item_code):
	from erpnext.stock.utils import get_valuation_method

	if not batch_nos:
		return {}

	shared_rate = get_valuation_method(item_code) == "Moving Average" and frappe.get_single_value(
		"Stock Settings", "do_not_use_batchwise_valuation"
	)
	batches = frappe.get_all(
		"Batch",
		filters={"name": ("in", list(batch_nos))},
		fields=["name", "batch_id", "use_batchwise_valuation"],
	)
	return {
		batch.name: frappe._dict(
			batch_id=batch.batch_id or batch.name,
			own_rate=bool(batch.use_batchwise_valuation) and not shared_rate,
		)
		for batch in batches
	}


def get_stock_gap(last_row, stock_parts, mismatches):
	parts_value = sum(flt(part.value) for part in stock_parts)
	gap = flt(last_row.stock_value) - parts_value
	if not is_different(gap, 0):
		return None

	causes = sorted(mismatches.values(), key=lambda mismatch: -abs(mismatch.gap))
	return frappe._dict(
		ledger_value=flt(last_row.stock_value),
		parts_value=parts_value,
		gap=gap,
		causes=causes[:MISMATCHES_SHOWN],
		more_causes=max(len(causes) - MISMATCHES_SHOWN, 0),
		explained=sum(mismatch.gap for mismatch in causes),
	)


def set_labels(entries, result, valued_by):
	parts = [part for entry in entries for part in entry.get("parts", [])]
	if valued_by == "serial":
		groups = parts + list(result.stock_parts)
		causes = result.stock_gap.causes if result.stock_gap else []
		set_serial_labels(groups, causes)

	set_source_returns(parts)


def set_serial_labels(groups, causes):
	names = {serial_no for group in groups + causes for serial_no in group.serial_nos}
	if not names:
		return

	labels = dict(
		frappe.get_all(
			"Serial No", filters={"name": ("in", list(names))}, fields=["name", "serial_no"], as_list=True
		)
	)
	for group in groups + causes:
		group.serial_labels = [labels.get(serial_no) or serial_no for serial_no in group.serial_nos]


def set_source_returns(parts):
	returns = set()
	for doctype in RETURN_DOCTYPES:
		names = {part.source_voucher_no for part in parts if part.get("source_voucher_type") == doctype}
		if names:
			returns.update(
				frappe.get_all(doctype, filters={"name": ("in", list(names)), "is_return": 1}, pluck="name")
			)

	for part in parts:
		part.source_is_return = part.get("source_voucher_no") in returns

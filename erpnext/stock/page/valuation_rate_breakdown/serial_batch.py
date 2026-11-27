import frappe
from frappe.query_builder.functions import Abs, Count, Sum
from frappe.utils import cint, create_batch, flt

from erpnext.stock.page.valuation_rate_breakdown import legacy
from erpnext.stock.serial_batch_bundle import SERIAL_NO_QUERY_BATCH_SIZE

SERIALS_SHOWN = 10
MISMATCHES_SHOWN = 5
TRACED_SERIALS = 200
ROUNDING_GAP = 1
RETURN_DOCTYPES = ("Purchase Receipt", "Purchase Invoice", "Delivery Note", "Sales Invoice")


def set_serial_batch_details(entries, rows, item, warehouse, focus=None):
	if not rows:
		return

	focus_name = focus.name if focus else None
	if item.valued_by == "serial":
		book = make_serial_book(item.item_code, warehouse, rows, focus_name)
	else:
		book = make_batch_book(item.item_code, warehouse, rows, focus_name)

	parts = []
	for entry in entries:
		entry.parts = book.entry_parts(entry.name)
		parts.extend(entry.parts)

	if item.valued_by == "serial":
		set_serial_labels(parts)

	set_source_returns(parts)


def get_stock_summary(item, warehouse, anchor):
	if item.valued_by == "serial":
		held, mismatches = get_serial_summary(item.item_code, warehouse, anchor)
		stock_parts = group_serials(held)
	else:
		stock_parts, mismatches = get_batch_parts(item.item_code, warehouse, anchor), {}

	stock_gap = get_stock_gap(anchor, stock_parts, mismatches)
	if item.valued_by == "serial":
		set_serial_labels(stock_parts + (stock_gap.causes if stock_gap else []))

	return frappe._dict(stock_parts=stock_parts, stock_gap=stock_gap)


def make_serial_book(item_code, warehouse, rows, focus_name):
	book = SerialBook(focus_name)
	window = {row.name for row in rows}
	if focus_name:
		history = get_serial_history(item_code, warehouse, [focus_name], rows[-1])
	else:
		history = get_window_serial_history(item_code, warehouse, rows)

	for row in history:
		book.add(row, row.sle in window)

	return book


def make_batch_book(item_code, warehouse, rows, focus_name):
	lines = get_window_lines(rows)
	batch_nos = {line.batch_no for line in lines if line.batch_no}
	totals = get_entry_totals(item_code, warehouse, rows[0], "batch_no", batch_nos, inclusive=False)
	opening = {batch_no: [total.qty, total.value] for batch_no, total in totals.items()}
	book = BatchBook(get_batches(batch_nos, item_code), opening, focus_name)
	for line in lines:
		book.add(line)

	return book


def get_window_lines(rows):
	lines = get_bundle_lines(rows) + legacy.window_lines(rows)
	position = {row.name: index for index, row in enumerate(rows)}
	return sorted(lines, key=lambda line: (position[line.sle], line.idx))


def get_bundle_lines(rows):
	by_bundle = {row.serial_and_batch_bundle: row for row in rows if row.serial_and_batch_bundle}
	if not by_bundle:
		return []

	entry = frappe.qb.DocType("Serial and Batch Entry")
	lines = (
		frappe.qb.from_(entry)
		.select(entry.parent, entry.serial_no, entry.batch_no, entry.qty, entry.stock_value_difference)
		.select(entry.idx)
		.where(entry.parent.isin(list(by_bundle)) & (entry.docstatus == 1) & (entry.is_cancelled == 0))
		.run(as_dict=True)
	)
	for line in lines:
		row = by_bundle[line.parent]
		line.update(sle=row.name, voucher_type=row.voucher_type, voucher_no=row.voucher_no)
		line.posting_date = row.posting_date

	return lines


def get_window_serial_history(item_code, warehouse, rows):
	legacy_serials = {line.serial_no for line in legacy.window_lines(rows) if line.serial_no}
	bundles = [row.serial_and_batch_bundle for row in rows if row.serial_and_batch_bundle]
	if not bundles:
		return get_serial_history(item_code, warehouse, legacy_serials, rows[-1])

	window = frappe.qb.DocType("Serial and Batch Entry").as_("window_entry")
	serials = frappe.qb.from_(window).select(window.serial_no).distinct().where(window.parent.isin(bundles))
	serial_nos = serials.limit(SERIAL_NO_QUERY_BATCH_SIZE + 1).run(pluck=True)
	if len(serial_nos) <= SERIAL_NO_QUERY_BATCH_SIZE:
		return get_serial_history(item_code, warehouse, set(serial_nos) | legacy_serials, rows[-1])

	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = serial_history_query(item_code, warehouse, serials, rows[-1]).where(
		(sle.item_code == item_code) & (sle.warehouse == warehouse)
	)
	history = query.run(as_dict=True)
	wanted = {row.serial_no for row in history} | legacy_serials
	history.extend(legacy.get_serial_lines(item_code, warehouse, rows[-1], wanted))
	return sorted(history, key=history_order)


def get_serial_history(item_code, warehouse, serial_nos, last_row):
	rows = []
	serial_nos = sorted({serial_no for serial_no in serial_nos if serial_no})
	for chunk in create_batch(serial_nos, SERIAL_NO_QUERY_BATCH_SIZE):
		rows.extend(serial_history_query(item_code, warehouse, chunk, last_row).run(as_dict=True))

	if serial_nos:
		rows.extend(legacy.get_serial_lines(item_code, warehouse, last_row, serial_nos))

	return sorted(rows, key=history_order)


def history_order(row):
	return (row.posting_datetime, row.creation, row.idx)


def serial_history_query(item_code, warehouse, serial_nos, last_row):
	entry = frappe.qb.DocType("Serial and Batch Entry")
	sle = frappe.qb.DocType("Stock Ledger Entry")
	same_time = (entry.posting_datetime == last_row.posting_datetime) & (sle.creation <= last_row.creation)
	return (
		frappe.qb.from_(entry)
		.inner_join(sle)
		.on((sle.serial_and_batch_bundle == entry.parent) & (sle.is_cancelled == 0))
		.select(entry.serial_no, entry.batch_no, entry.qty, entry.stock_value_difference, entry.idx)
		.select(sle.name.as_("sle"), sle.voucher_type, sle.voucher_no, sle.posting_date)
		.select(sle.posting_datetime, sle.creation)
		.where(
			entry.serial_no.isin(serial_nos)
			& (entry.warehouse == warehouse)
			& (entry.item_code == item_code)
			& ((entry.posting_datetime < last_row.posting_datetime) | same_time)
			& (entry.docstatus == 1)
			& (entry.is_cancelled == 0)
		)
	)


def get_entry_totals(item_code, warehouse, row, field, names=None, inclusive=True):
	if names is not None and not names:
		return {}

	totals = {}
	for query, entry in totals_queries(item_code, warehouse, row, inclusive):
		query = (
			query.select(entry[field].as_("key"), Sum(entry.qty).as_("qty"), Count(entry.name).as_("moves"))
			.select(Sum(entry.stock_value_difference).as_("value"))
			.groupby(entry[field])
		)
		if names is None:
			query = query.where(entry[field].isnotnull()).having(
				(Abs(Sum(entry.qty)) >= 0.000001) | (Abs(Sum(entry.stock_value_difference)) >= 0.005)
			)
		else:
			query = query.where(entry[field].isin(list(names)))

		for part in query.run(as_dict=True):
			add_to_total(totals, part)

	for part in legacy.get_totals(item_code, warehouse, row, field, names, inclusive):
		add_to_total(totals, part)

	return totals


def totals_queries(item_code, warehouse, row, inclusive):
	entry = frappe.qb.DocType("Serial and Batch Entry")
	sle = frappe.qb.DocType("Stock Ledger Entry")
	condition = (
		(entry.item_code == item_code)
		& (entry.warehouse == warehouse)
		& (entry.docstatus == 1)
		& (entry.is_cancelled == 0)
	)
	creation = sle.creation <= row.creation if inclusive else sle.creation < row.creation
	earlier = frappe.qb.from_(entry).where(condition & (entry.posting_datetime < row.posting_datetime))
	same_time = (
		frappe.qb.from_(entry)
		.inner_join(sle)
		.on((sle.serial_and_batch_bundle == entry.parent) & (sle.is_cancelled == 0))
		.where(condition & (entry.posting_datetime == row.posting_datetime) & creation)
	)
	return [(earlier, entry), (same_time, entry)]


def add_to_total(totals, part):
	if not part.key:
		return

	total = totals.setdefault(part.key, frappe._dict(qty=0.0, value=0.0, moves=0))
	total.qty += flt(part.qty)
	total.value += flt(part.value)
	total.moves += part.moves


def get_serial_summary(item_code, warehouse, anchor):
	totals = get_entry_totals(item_code, warehouse, anchor, "serial_no")
	held = {serial: total.value for serial, total in totals.items() if total.qty > 0 and total.moves == 1}
	moved_again = [serial for serial, total in totals.items() if total.qty > 0 and total.moves > 1]
	left_value = [
		serial for serial, total in totals.items() if total.qty <= 0 and is_different(total.value, 0)
	]
	left_value.sort(key=lambda serial: -abs(totals[serial].value))
	book = SerialBook()
	for row in get_serial_history(item_code, warehouse, moved_again + left_value[:TRACED_SERIALS], anchor):
		book.add(row, False)

	held.update({serial_no: source.rate for serial_no, source in book.held.items()})
	return held, book.mismatches


def group_serials(held):
	groups = {}
	for serial_no, rate in held.items():
		group = groups.setdefault(
			flt(rate, 2), frappe._dict(serial_nos=[], more=0, qty=0.0, value=0.0, rate=rate)
		)
		add_serial(group, serial_no, 1, rate)

	return sorted(groups.values(), key=lambda group: -group.qty)


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
			if source and row.legacy:
				rate = source.rate
			elif source and is_different(source.rate, rate):
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
	def __init__(self, batches, balances, focus=None):
		self.batches = batches
		self.balances = balances
		self.focus = focus
		self.parts = {}

	def add(self, row):
		if not row.batch_no:
			return

		balance = self.balances.setdefault(row.batch_no, [0.0, 0.0])
		qty, value = flt(row.qty), flt(row.stock_value_difference)
		if self.focus in (None, row.batch_no):
			self.add_part(row, balance, qty, value)

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

	def entry_parts(self, name):
		parts = list(self.parts.get(name, {}).values())
		for part in parts:
			part.rate = unit_rate(part.qty, part.value)
			part.qty_after = part.qty_before + part.qty
			part.value_after = part.value_before + part.value

		return parts


def get_batch_parts(item_code, warehouse, last_row):
	totals = get_entry_totals(item_code, warehouse, last_row, "batch_no")
	batches = get_batches(set(totals), item_code)
	parts, shared = [], frappe._dict(shared=True, count=0, qty=0.0, value=0.0)
	for batch_no, total in totals.items():
		qty, value = total.qty, total.value
		if not flt(qty, 6) and not is_different(value, 0):
			continue

		batch = batches.get(batch_no, frappe._dict())
		if not batch.own_rate:
			shared.update(count=shared.count + 1, qty=shared.qty + qty, value=shared.value + value)
			continue

		parts.append(
			frappe._dict(batch_no=batch_no, batch_id=batch.batch_id or batch_no, qty=qty, value=value)
		)

	parts.sort(key=lambda part: -part.qty)
	if shared.count:
		parts.append(shared)

	for part in parts:
		part.rate = unit_rate(part.qty, part.value)

	return parts


def uses_shared_batch_rate(valuation_method):
	return valuation_method == "Moving Average" and bool(
		frappe.get_single_value("Stock Settings", "do_not_use_batchwise_valuation")
	)


def get_batch_valuation(item_code, valuation_method):
	if uses_shared_batch_rate(valuation_method):
		return "shared"

	batch = frappe.qb.DocType("Batch")
	flags = {
		cint(flag)
		for flag in frappe.qb.from_(batch)
		.select(batch.use_batchwise_valuation)
		.distinct()
		.where(batch.item == item_code)
		.run(pluck=True)
	}
	if 0 not in flags:
		return "own"

	return "mixed" if 1 in flags else "shared"


def get_batches(batch_nos, item_code):
	from erpnext.stock.utils import get_valuation_method

	if not batch_nos:
		return {}

	shared_rate = uses_shared_batch_rate(get_valuation_method(item_code))
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
	if abs(gap) < ROUNDING_GAP:
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


def set_serial_labels(groups):
	names = {serial_no for group in groups for serial_no in group.serial_nos}
	if not names:
		return

	labels = dict(
		frappe.get_all(
			"Serial No", filters={"name": ("in", list(names))}, fields=["name", "serial_no"], as_list=True
		)
	)
	for group in groups:
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

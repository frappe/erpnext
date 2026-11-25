import frappe
from frappe.query_builder.functions import Concat, Count, Locate, Min, Sum
from frappe.utils import flt
from pypika.terms import Criterion

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

SQL_FILTERED_SERIALS = 50


def is_legacy(row):
	return not row.serial_and_batch_bundle and bool(row.batch_no or row.serial_no)


def parse_serials(row):
	return get_serial_nos(row.serial_no) if row.serial_no else []


def serial_moves(row, wanted=None, serial_nos=None):
	serial_nos = parse_serials(row) if serial_nos is None else serial_nos
	if not serial_nos:
		return []

	sign = 1 if flt(row.actual_qty) > 0 else -1
	value = flt(row.stock_value_difference) / len(serial_nos)
	return [
		(index, serial_no, sign, value)
		for index, serial_no in enumerate(serial_nos)
		if wanted is None or serial_no in wanted
	]


def to_lines(row, wanted=None):
	base = dict(
		sle=row.name,
		voucher_type=row.voucher_type,
		voucher_no=row.voucher_no,
		posting_date=row.posting_date,
		posting_datetime=row.posting_datetime,
		creation=row.creation,
		batch_no=row.batch_no or None,
		legacy=1,
	)
	serial_nos = parse_serials(row)
	if not serial_nos:
		qty, value = flt(row.actual_qty), flt(row.stock_value_difference)
		return [frappe._dict(base, idx=0, serial_no=None, qty=qty, stock_value_difference=value)]

	return [
		frappe._dict(base, idx=index, serial_no=serial_no, qty=qty, stock_value_difference=value)
		for index, serial_no, qty, value in serial_moves(row, wanted, serial_nos)
	]


def has_legacy_rows(item_code, warehouse):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	in_warehouse = (sle.item_code == item_code) & (sle.warehouse == warehouse)
	[first_created] = frappe.qb.from_(sle).select(Min(sle.creation)).where(in_warehouse).run(pluck=True)
	if not first_created:
		return False

	first = (
		frappe.qb.from_(sle)
		.select(sle.serial_and_batch_bundle, sle.batch_no, sle.serial_no)
		.where(in_warehouse & (sle.creation == first_created))
		.limit(1)
		.run(as_dict=True)
	)
	return bool(first) and is_legacy(first[0])


def window_lines(rows):
	return [line for row in rows if is_legacy(row) for line in to_lines(row)]


def legacy_condition(sle, item_code, warehouse, row, inclusive=True):
	creation = sle.creation <= row.creation if inclusive else sle.creation < row.creation
	return (
		(sle.item_code == item_code)
		& (sle.warehouse == warehouse)
		& (sle.is_cancelled == 0)
		& sle.serial_and_batch_bundle.isnull()
		& (
			(sle.posting_datetime < row.posting_datetime)
			| ((sle.posting_datetime == row.posting_datetime) & creation)
		)
	)


def has_serial(sle, serial_no):
	padded = Locate(f"\n{serial_no}\n", Concat("\n", sle.serial_no, "\n")) > 0
	return (Locate(serial_no, sle.serial_no) > 0) & padded


def focus_condition(sle, focus):
	if focus.field == "batch_no":
		return sle.serial_and_batch_bundle.isnull() & (sle.batch_no == focus.name)

	return sle.serial_and_batch_bundle.isnull() & has_serial(sle, focus.name)


def get_totals(item_code, warehouse, row, field, names=None, inclusive=True):
	if not has_legacy_rows(item_code, warehouse):
		return []

	if field == "batch_no":
		return get_batch_totals(item_code, warehouse, row, names, inclusive)

	wanted = set(names) if names is not None else None
	totals = {}
	for legacy_row in get_serial_rows(item_code, warehouse, row, wanted, inclusive):
		for _index, serial_no, qty, value in serial_moves(legacy_row, wanted):
			total = totals.setdefault(serial_no, frappe._dict(key=serial_no, qty=0.0, value=0.0, moves=0))
			total.qty += qty
			total.value += value
			total.moves += 1

	return list(totals.values())


def get_batch_totals(item_code, warehouse, row, names=None, inclusive=True):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = (
		frappe.qb.from_(sle)
		.select(sle.batch_no.as_("key"), Sum(sle.actual_qty).as_("qty"), Count(sle.name).as_("moves"))
		.select(Sum(sle.stock_value_difference).as_("value"))
		.where(legacy_condition(sle, item_code, warehouse, row, inclusive))
		.groupby(sle.batch_no)
	)
	if names is None:
		query = query.where(sle.batch_no.isnotnull() & (sle.batch_no != ""))
	else:
		query = query.where(sle.batch_no.isin(list(names)))

	return query.run(as_dict=True)


def get_serial_lines(item_code, warehouse, row, serial_nos=None, inclusive=True):
	if not has_legacy_rows(item_code, warehouse):
		return []

	wanted = set(serial_nos) if serial_nos is not None else None
	rows = get_serial_rows(item_code, warehouse, row, wanted, inclusive)
	return [line for legacy_row in rows for line in to_lines(legacy_row, wanted)]


def get_serial_rows(item_code, warehouse, row, wanted=None, inclusive=True):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = (
		frappe.qb.from_(sle)
		.select(sle.name, sle.voucher_type, sle.voucher_no, sle.posting_date, sle.posting_datetime)
		.select(sle.creation, sle.actual_qty, sle.stock_value_difference, sle.serial_no, sle.batch_no)
		.select(sle.serial_and_batch_bundle)
		.where(legacy_condition(sle, item_code, warehouse, row, inclusive))
		.where(sle.serial_no.isnotnull() & (sle.serial_no != ""))
	)
	if wanted is not None and len(wanted) <= SQL_FILTERED_SERIALS:
		if not wanted:
			return []

		query = query.where(Criterion.any([has_serial(sle, serial_no) for serial_no in sorted(wanted)]))

	return query.run(as_dict=True)

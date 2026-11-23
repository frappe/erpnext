import frappe
from frappe.query_builder import Order
from frappe.utils import flt

SERIALS_SHOWN = 10


def set_serial_batch_details(entries, rows, valued_by, item_code, warehouse):
	bundles = {row.serial_and_batch_bundle: row for row in rows if row.serial_and_batch_bundle}
	if not bundles:
		return

	bundle_rows = get_bundle_rows(list(bundles))
	if valued_by == "batch":
		parts = get_batch_parts(bundles, bundle_rows, item_code, warehouse)
	else:
		parts = get_serial_parts(bundles, bundle_rows, item_code, warehouse)

	for entry in entries:
		entry.parts = parts.get(entry.name, [])


def get_bundle_rows(bundles):
	entry = frappe.qb.DocType("Serial and Batch Entry")
	return (
		frappe.qb.from_(entry)
		.select(entry.parent, entry.serial_no, entry.batch_no, entry.qty, entry.stock_value_difference)
		.where(entry.parent.isin(bundles))
		.orderby(entry.idx)
		.run(as_dict=True)
	)


def get_batch_parts(bundles, bundle_rows, item_code, warehouse):
	totals = {}
	for row in bundle_rows:
		key = (bundles[row.parent].name, row.batch_no)
		total = totals.setdefault(key, frappe._dict(batch_no=row.batch_no, qty=0.0, value=0.0))
		total.qty += flt(row.qty)
		total.value += flt(row.stock_value_difference)

	batches = get_batches({row.batch_no for row in bundle_rows}, item_code)
	own_rate_batches = {name for name, batch in batches.items() if batch.own_rate}
	balances = get_batch_balances_before(bundles, own_rate_batches, item_code, warehouse)
	parts = {}
	for (entry_name, batch_no), total in totals.items():
		total.rate = abs(total.value / total.qty) if total.qty else 0.0
		total.batch_id = batches[batch_no].batch_id if batch_no in batches else batch_no
		total.own_rate = batch_no in own_rate_batches
		if total.own_rate:
			total.qty_before, total.value_before = balances.get((entry_name, batch_no), (0.0, 0.0))

		parts.setdefault(entry_name, []).append(total)

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


def get_batch_balances_before(bundles, batch_nos, item_code, warehouse):
	if not batch_nos:
		return {}

	window = {row.name for row in bundles.values()}
	upto = max(row.posting_datetime for row in bundles.values())
	balances, before = {}, {}
	for row in get_batch_history(batch_nos, item_code, warehouse, upto):
		balance = balances.setdefault(row.batch_no, [0.0, 0.0])
		if row.sle in window:
			before.setdefault((row.sle, row.batch_no), tuple(balance))

		balance[0] += flt(row.qty)
		balance[1] += flt(row.stock_value_difference)

	return before


def get_batch_history(batch_nos, item_code, warehouse, upto):
	entry = frappe.qb.DocType("Serial and Batch Entry")
	sle = frappe.qb.DocType("Stock Ledger Entry")
	return (
		frappe.qb.from_(entry)
		.inner_join(sle)
		.on((sle.serial_and_batch_bundle == entry.parent) & (sle.is_cancelled == 0))
		.select(entry.batch_no, entry.qty, entry.stock_value_difference, sle.name.as_("sle"))
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (sle.posting_datetime <= upto)
			& (entry.batch_no.isin(list(batch_nos)))
			& (entry.docstatus == 1)
			& (entry.is_cancelled == 0)
		)
		.orderby(sle.posting_datetime)
		.orderby(sle.creation)
		.run(as_dict=True)
	)


def get_serial_parts(bundles, bundle_rows, item_code, warehouse):
	outward_serials = [row.serial_no for row in bundle_rows if row.serial_no and flt(row.qty) < 0]
	sources = get_serial_sources(outward_serials, item_code, warehouse)
	parts = {}
	for row in bundle_rows:
		if not row.serial_no:
			continue

		sle = bundles[row.parent]
		source = find_source(sources.get(row.serial_no, []), sle) if flt(row.qty) < 0 else None
		add_serial_to_group(parts.setdefault(sle.name, {}), row, source)

	set_serial_labels(parts)
	return {name: list(groups.values()) for name, groups in parts.items()}


def set_serial_labels(parts):
	groups = [group for entry_groups in parts.values() for group in entry_groups.values()]
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


def get_serial_sources(serial_nos, item_code, warehouse):
	if not serial_nos:
		return {}

	entry = frappe.qb.DocType("Serial and Batch Entry")
	sle = frappe.qb.DocType("Stock Ledger Entry")
	rows = (
		frappe.qb.from_(entry)
		.inner_join(sle)
		.on((sle.serial_and_batch_bundle == entry.parent) & (sle.is_cancelled == 0))
		.select(entry.serial_no, entry.incoming_rate, sle.voucher_type, sle.voucher_no)
		.select(sle.posting_date, sle.posting_datetime)
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (entry.serial_no.isin(serial_nos))
			& (entry.qty > 0)
			& (entry.docstatus == 1)
			& (entry.is_cancelled == 0)
		)
		.orderby(sle.posting_datetime, order=Order.desc)
		.orderby(sle.creation, order=Order.desc)
		.run(as_dict=True)
	)
	sources = {}
	for row in rows:
		sources.setdefault(row.serial_no, []).append(row)

	return sources


def find_source(sources, sle):
	for source in sources:
		if source.posting_datetime <= sle.posting_datetime and source.voucher_no != sle.voucher_no:
			return source

	return None


def add_serial_to_group(groups, row, source):
	qty = flt(row.qty)
	value = flt(row.stock_value_difference)
	rate = abs(value / qty) if qty else 0.0
	key = (flt(rate, 2), source.voucher_no if source else None)
	group = groups.setdefault(key, frappe._dict(serial_nos=[], more=0, qty=0.0, value=0.0, rate=rate))
	if source:
		group.update(
			source_voucher_type=source.voucher_type,
			source_voucher_no=source.voucher_no,
			source_date=source.posting_date,
		)

	group.qty += qty
	group.value += value
	if len(group.serial_nos) < SERIALS_SHOWN:
		group.serial_nos.append(row.serial_no)
	else:
		group.more += 1

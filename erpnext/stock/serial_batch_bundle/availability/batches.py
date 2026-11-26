from collections import defaultdict

import frappe
import frappe.query_builder
from frappe.query_builder.functions import Max, Sum
from frappe.utils import flt, getdate, today

from erpnext.stock.serial_batch_bundle.availability.reservations import (
	get_batches_to_be_considered,
	get_cross_warehouse_sre_details,
	get_reserved_batches_for_pos,
	get_reserved_batches_for_sre,
)


def get_batch_qty_for_stock(batch_no=None, warehouse=None, posting_date=None, posting_time=None, **kwargs):
	"""Internal stock calculations must include quantities in all relevant warehouses."""
	from erpnext.stock.utils import get_combine_datetime

	kwargs = frappe._dict(kwargs)
	kwargs.update(
		batch_no=batch_no,
		warehouse=warehouse,
		based_on=frappe.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"),
	)
	if not kwargs.posting_datetime and posting_date:
		kwargs.posting_datetime = get_combine_datetime(posting_date, posting_time)

	batches = get_auto_batch_nos(kwargs)
	if batch_no and warehouse:
		return sum(row.qty for row in batches if row.batch_no == batch_no)

	return batches


def get_auto_batch_nos(kwargs):
	from erpnext.stock.utils import get_combine_datetime

	if kwargs.against_sales_order and (
		only_consider_batches := get_batches_to_be_considered(kwargs.against_sales_order)
	):
		batches, warehouses = [], []
		for item in only_consider_batches:
			batches.append(item.batch_no)
			warehouses.append(item.warehouse)

		if batches:
			kwargs.batch_no = batches
			kwargs.warehouse = warehouses

	if not kwargs.get("posting_datetime") and kwargs.get("posting_date"):
		kwargs["posting_datetime"] = get_combine_datetime(
			kwargs.get("posting_date"), kwargs.get("posting_time")
		)

	available_batches = get_available_batches(kwargs)
	stock_ledgers_batches = get_stock_ledgers_batches(kwargs)

	pos_invoice_batches = frappe._dict()
	if not kwargs.for_stock_levels:
		pos_invoice_batches = get_reserved_batches_for_pos(kwargs)

	sre_reserved_batches = frappe._dict()
	if not kwargs.ignore_reserved_stock:
		sre_reserved_batches = get_reserved_batches_for_sre(kwargs)

	if kwargs.against_sales_order and only_consider_batches:
		kwargs.batch_no = kwargs.warehouse = None

	picked_batches = frappe._dict()
	if kwargs.get("is_pick_list"):
		picked_batches = get_picked_batches(kwargs)

	update_available_batches(available_batches, stock_ledgers_batches)
	# a reservation of a batch that is not available (e.g. expired) has nothing to reduce
	update_available_batches(
		available_batches,
		pos_invoice_batches,
		sre_reserved_batches,
		picked_batches,
		kwargs.get("already_picked_batches"),
		add_missing=False,
	)

	if not kwargs.ignore_reserved_stock and not kwargs.for_stock_levels:
		available_batches = remove_reservation_conflict_batches(available_batches, kwargs)

	if kwargs.based_on == "Expiry":
		available_batches = sorted(available_batches, key=lambda x: x.expiry_date or getdate("9999-12-31"))

	if not kwargs.get("do_not_check_future_batches") and available_batches and kwargs.get("posting_datetime"):
		filter_zero_near_batches(available_batches, kwargs)

	if not kwargs.consider_negative_batches:
		precision = frappe.get_precision("Stock Ledger Entry", "actual_qty")
		available_batches = [d for d in available_batches if flt(d.qty, precision) > 0]

	qty = flt(kwargs.qty)

	if not qty:
		return available_batches

	return get_qty_based_available_batches(available_batches, qty)


def remove_reservation_conflict_batches(available_batches, kwargs):
	if not available_batches or not frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
		return available_batches

	conflicting_batches = get_cross_warehouse_reserved_batches(kwargs)
	if not conflicting_batches:
		return available_batches

	return [d for d in available_batches if d.batch_no not in conflicting_batches]


def get_cross_warehouse_reserved_batches(kwargs) -> set:
	conflicting_batches = set()
	for row in get_cross_warehouse_sre_details(kwargs):
		if flt(row.outstanding_qty) <= 0:
			continue

		batch_qty = get_batch_qty_for_stock(
			row.batch_no,
			row.warehouse,
			posting_date=kwargs.get("posting_date"),
			posting_time=kwargs.get("posting_time"),
			consider_negative_batches=True,
		)

		if flt(batch_qty, 6) < flt(row.outstanding_qty, 6):
			conflicting_batches.add(row.batch_no)

	return conflicting_batches


def get_batch_nos_from_sre(kwargs):
	from frappe.query_builder.functions import Sum

	table = frappe.qb.DocType("Stock Reservation Entry")
	child_table = frappe.qb.DocType("Serial and Batch Entry")
	batch = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(table)
		.join(child_table)
		.on(table.name == child_table.parent)
		.left_join(batch)
		.on(batch.name == child_table.batch_no)
		.select(
			child_table.batch_no,
			child_table.warehouse,
			Sum(child_table.qty - child_table.delivered_qty).as_("qty"),
		)
		.where(
			(table.docstatus == 1)
			& (table.voucher_detail_no == kwargs.scio_detail)
			& (child_table.qty != child_table.delivered_qty)
		)
		.groupby(child_table.batch_no, child_table.warehouse, batch.batch_id)
		.orderby(batch.batch_id, order=frappe.query_builder.Order.asc)
	)

	result = query.run(as_dict=True)
	return get_qty_based_available_batches(result, flt(kwargs.qty)) if flt(kwargs.qty) else result


def filter_zero_near_batches(available_batches, kwargs):
	kwargs.batch_no = [d.batch_no for d in available_batches]

	del kwargs["posting_datetime"]

	kwargs.do_not_check_future_batches = 1
	available_batches_in_future = get_auto_batch_nos(kwargs)
	for batch in available_batches:
		if batch.qty <= 0:
			continue

		for future_batch in available_batches_in_future:
			if (
				batch.batch_no == future_batch.batch_no
				and batch.warehouse == future_batch.warehouse
				and future_batch.qty <= 0
			):
				batch.qty = 0


def get_qty_based_available_batches(available_batches, qty):
	precision = frappe.get_precision("Stock Ledger Entry", "actual_qty")
	batches = []
	for batch in available_batches:
		if flt(qty, precision) <= 0:
			break

		batch_qty = flt(batch.qty)
		if qty > batch_qty:
			batches.append(
				frappe._dict(
					{
						"batch_no": batch.batch_no,
						"qty": batch_qty,
						"warehouse": batch.warehouse,
					}
				)
			)
			qty -= batch_qty
		else:
			batches.append(
				frappe._dict(
					{
						"batch_no": batch.batch_no,
						"qty": qty,
						"warehouse": batch.warehouse,
					}
				)
			)
			qty = 0

	return batches


def update_available_batches(available_batches, *reserved_batches, add_missing=True) -> None:
	"""Add each batch's qty to its available row; with add_missing, a batch with no row is appended."""
	precision = frappe.get_precision("Stock Ledger Entry", "actual_qty")
	for batches in reserved_batches:
		if batches:
			for key, data in batches.items():
				batch_no, warehouse = key
				batch_not_exists = True
				for batch in available_batches:
					if batch.batch_no == batch_no and batch.warehouse == warehouse:
						batch.qty = flt(batch.qty + data.qty, precision)
						batch_not_exists = False

				if batch_not_exists and add_missing:
					available_batches.append(data)


def get_available_batches(kwargs):
	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	batch_ledger = frappe.qb.DocType("Serial and Batch Entry")
	batch_table = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(stock_ledger_entry)
		.inner_join(batch_ledger)
		.on(stock_ledger_entry.serial_and_batch_bundle == batch_ledger.parent)
		.inner_join(batch_table)
		.on(batch_ledger.batch_no == batch_table.name)
		.select(
			batch_ledger.batch_no,
			batch_ledger.warehouse,
			Sum(batch_ledger.qty).as_("qty"),
			Max(batch_table.expiry_date).as_("expiry_date"),
		)
		.where(stock_ledger_entry.is_cancelled == 0)
		.groupby(batch_ledger.batch_no, batch_ledger.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(stock_ledger_entry.company == kwargs.get("company"))

	if not kwargs.get("for_stock_levels"):
		query = query.where(batch_table.disabled == 0)
		query = query.where((batch_table.expiry_date >= today()) | (batch_table.expiry_date.isnull()))

	if kwargs.get("posting_datetime"):
		timestamp_condition = stock_ledger_entry.posting_datetime <= kwargs.posting_datetime

		if kwargs.get("creation"):
			timestamp_condition = stock_ledger_entry.posting_datetime < kwargs.posting_datetime

			timestamp_condition |= (stock_ledger_entry.posting_datetime == kwargs.posting_datetime) & (
				stock_ledger_entry.creation < kwargs.creation
			)

		query = query.where(timestamp_condition)

	for field in ["warehouse", "item_code"]:
		if not kwargs.get(field):
			continue

		if isinstance(kwargs.get(field), list):
			query = query.where(stock_ledger_entry[field].isin(kwargs.get(field)))
		else:
			query = query.where(stock_ledger_entry[field] == kwargs.get(field))

	if kwargs.get("batch_no"):
		if isinstance(kwargs.batch_no, list):
			query = query.where(batch_ledger.batch_no.isin(kwargs.batch_no))
		else:
			query = query.where(batch_ledger.batch_no == kwargs.batch_no)

	# order by aggregates (one row per batch_no+warehouse); raw columns aren't valid under GROUP BY on postgres
	if kwargs.based_on == "LIFO":
		query = query.orderby(Max(batch_table.creation), order=frappe.qb.desc)
	elif kwargs.based_on == "Expiry":
		query = query.orderby(Max(batch_table.expiry_date))
	else:
		query = query.orderby(Max(batch_table.creation))

	if kwargs.get("ignore_voucher_nos"):
		query = query.where(stock_ledger_entry.voucher_no.notin(kwargs.get("ignore_voucher_nos")))

	data = query.run(as_dict=True)

	return data


def get_available_batches_qty(available_batches):
	available_batches_qty = defaultdict(float)
	for batch in available_batches:
		available_batches_qty[batch.batch_no] += batch.qty

	return available_batches_qty


def get_stock_ledgers_batches(kwargs):
	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	batch_table = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(stock_ledger_entry)
		.inner_join(batch_table)
		.on(stock_ledger_entry.batch_no == batch_table.name)
		.select(
			stock_ledger_entry.warehouse,
			Max(stock_ledger_entry.item_code).as_("item_code"),
			Sum(stock_ledger_entry.actual_qty).as_("qty"),
			stock_ledger_entry.batch_no,
			Max(batch_table.expiry_date).as_("expiry_date"),
		)
		.where((stock_ledger_entry.is_cancelled == 0) & (stock_ledger_entry.batch_no.isnotnull()))
		.groupby(stock_ledger_entry.batch_no, stock_ledger_entry.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(stock_ledger_entry.company == kwargs.get("company"))

	for field in ["warehouse", "item_code", "batch_no"]:
		if not kwargs.get(field):
			continue

		if isinstance(kwargs.get(field), list):
			query = query.where(stock_ledger_entry[field].isin(kwargs.get(field)))
		else:
			query = query.where(stock_ledger_entry[field] == kwargs.get(field))

	if not kwargs.get("for_stock_levels"):
		query = query.where((batch_table.expiry_date >= today()) | (batch_table.expiry_date.isnull()))

	if kwargs.get("posting_datetime"):
		timestamp_condition = stock_ledger_entry.posting_datetime <= kwargs.posting_datetime

		if kwargs.get("creation"):
			timestamp_condition = stock_ledger_entry.posting_datetime < kwargs.posting_datetime

			timestamp_condition |= (stock_ledger_entry.posting_datetime == kwargs.posting_datetime) & (
				stock_ledger_entry.creation < kwargs.creation
			)

		query = query.where(timestamp_condition)

	if kwargs.get("ignore_voucher_nos"):
		query = query.where(stock_ledger_entry.voucher_no.notin(kwargs.get("ignore_voucher_nos")))

	# order by aggregates (one row per batch_no+warehouse); raw columns aren't valid under GROUP BY on postgres
	if kwargs.based_on == "LIFO":
		query = query.orderby(Max(batch_table.creation), order=frappe.qb.desc)
	elif kwargs.based_on == "Expiry":
		query = query.orderby(Max(batch_table.expiry_date))
	else:
		query = query.orderby(Max(batch_table.creation))

	data = query.run(as_dict=True)
	batches = {}
	for d in data:
		key = (d.batch_no, d.warehouse)
		if key not in batches:
			batches[key] = d
		else:
			batches[key].qty += d.qty

	return batches


def get_picked_batches(kwargs) -> dict[str, dict]:
	picked_batches = frappe._dict()

	child_table = frappe.qb.DocType("Serial and Batch Entry")
	pick_list_table = frappe.qb.DocType("Pick List")

	query = (
		frappe.qb.from_(child_table)
		.inner_join(pick_list_table)
		.on(child_table.voucher_no == pick_list_table.name)
		.select(
			child_table.batch_no,
			child_table.warehouse,
			Sum(child_table.qty).as_("qty"),
		)
		.where(
			(child_table.docstatus != 2)
			& (pick_list_table.status != "Completed")
			& (child_table.type_of_transaction == "Outward")
			& (child_table.is_cancelled == 0)
			& (child_table.voucher_type == "Pick List")
			& (child_table.voucher_no.isnotnull())
		)
		.groupby(child_table.batch_no, child_table.warehouse)
	)

	if kwargs.get("company"):
		query = query.where(pick_list_table.company == kwargs.get("company"))

	if kwargs.get("item_code"):
		query = query.where(child_table.item_code == kwargs.get("item_code"))

	if kwargs.get("warehouse"):
		if isinstance(kwargs.warehouse, list):
			query = query.where(child_table.warehouse.isin(kwargs.warehouse))
		else:
			query = query.where(child_table.warehouse == kwargs.get("warehouse"))

	data = query.run(as_dict=True)
	for row in data:
		if not row.qty:
			continue

		key = (row.batch_no, row.warehouse)
		if key not in picked_batches:
			picked_batches[key] = frappe._dict(
				{
					"qty": row.qty,
					"warehouse": row.warehouse,
				}
			)
		else:
			picked_batches[key].qty += row.qty

	return picked_batches

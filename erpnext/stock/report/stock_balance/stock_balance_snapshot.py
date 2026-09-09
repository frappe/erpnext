# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.query_builder.functions import Abs, Min, Sum
from pypika import Case, CustomFunction
from pypika.analytics import CURRENT_ROW, Preceding, RowNumber
from pypika.analytics import Sum as WindowSum

ArgMaxNull = CustomFunction("arg_max_null", ["value", "order"])


def prepare_aggregated_balances(report):
	"""Aggregate movements between balance resets, then apply each reset in ledger order."""
	if report.filters.get("show_dimension_wise_stock") or any(
		report.filters.get(field) for field in report.inventory_dimensions
	):
		return False

	query = get_balance_query(report)
	for row in report.snapshot.run(query, as_dict=True, as_iterator=True):
		apply_segment(report, row)
	return True


def get_balance_query(report):
	entries = frappe.qb.Table("snapshot_entries")
	segments = frappe.qb.Table("snapshot_segments")
	segment_query = frappe.qb.from_(entries).select(
		entries.star,
		WindowSum(entries.snapshot_detail)
		.over(entries.item_code, entries.warehouse)
		.orderby(entries.snapshot_row)
		.rows(Preceding(), CURRENT_ROW)
		.as_("snapshot_segment"),
	)
	# Each detail row starts a segment and forms its own group, separate from ordinary movements.
	return (
		frappe.qb.with_(get_segment_query(report), "snapshot_entries")
		.with_(segment_query, "snapshot_segments")
		.from_(segments)
		.select(
			segments.item_code,
			segments.warehouse,
			segments.snapshot_detail,
			Min(segments.snapshot_row).as_("snapshot_row"),
			*get_latest_columns(report, segments),
			*get_movement_columns(segments),
		)
		.groupby(segments.item_code, segments.warehouse, segments.snapshot_segment, segments.snapshot_detail)
		.orderby("snapshot_row")
	)


def get_movement_columns(segments):
	columns = []
	for field, suffix in ((segments.actual_qty, "qty"), (segments.stock_value_difference, "val")):
		columns.extend(
			[
				Sum(Case().when(segments.snapshot_opening == 1, field).else_(0)).as_(f"opening_{suffix}"),
				Sum(Case().when((segments.snapshot_opening == 0) & (field >= 0), field).else_(0)).as_(
					f"in_{suffix}"
				),
				Sum(Case().when((segments.snapshot_opening == 0) & (field < 0), -field).else_(0)).as_(
					f"out_{suffix}"
				),
				Sum(field).as_(f"bal_{suffix}"),
			]
		)
	return columns


def get_segment_query(report):
	ledger = frappe.qb.DocType("Stock Ledger Entry")
	opening = ledger.posting_date < report.from_date
	for voucher_type, vouchers in report.opening_vouchers.items():
		if vouchers:
			opening |= (ledger.voucher_type == voucher_type) & ledger.voucher_no.isin(vouchers)

	# flt() can classify tiny negative amounts as incoming. Preserve its exact rounding rules.
	detail = ledger.voucher_type == "Stock Reconciliation"
	for field in (ledger.actual_qty, ledger.stock_value_difference):
		detail |= (field < 0) & (Abs(field) < 10**-report.float_precision)

	return report.sle_query.select(
		RowNumber().orderby(ledger.posting_datetime, ledger.creation).as_("snapshot_row"),
		Case().when(opening, 1).else_(0).as_("snapshot_opening"),
		Case().when(detail, 1).else_(0).as_("snapshot_detail"),
	)


def get_latest_columns(report, segments):
	fields = [
		"company",
		"item_group",
		"stock_uom",
		"item_name",
		"valuation_rate",
		*report.inventory_dimensions,
		"posting_date",
		"actual_qty",
		"stock_value_difference",
		"voucher_type",
		"voucher_no",
		"batch_no",
		"serial_no",
		"serial_and_batch_bundle",
		"qty_after_transaction",
		"stock_value",
		"voucher_detail_no",
	]
	return [ArgMaxNull(segments[field], segments.snapshot_row).as_(field) for field in fields]


def apply_segment(report, row):
	key = report.get_group_by_key(row)
	if key not in report.item_warehouse_map:
		report.initialize_data(key, row)

	if row.snapshot_detail:
		if row.voucher_type == "Stock Reconciliation" and not hasattr(
			report, "stock_reco_voucher_wise_count"
		):
			report.prepare_stock_reco_voucher_wise_count()
		report.prepare_item_warehouse_map(row, key)
		return

	balance = report.item_warehouse_map[key]
	for field in (
		"opening_qty",
		"opening_val",
		"in_qty",
		"in_val",
		"out_qty",
		"out_val",
		"bal_qty",
		"bal_val",
	):
		balance[field] += row[field]
	balance.val_rate = row.valuation_rate
	for field in report.inventory_dimensions:
		balance[field] = row.get(field)

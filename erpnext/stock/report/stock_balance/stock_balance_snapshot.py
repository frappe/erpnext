# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import pyarrow as pa
from frappe import _
from frappe.database.duckdb.database import get_latest_sync
from frappe.utils import getdate

from erpnext.stock.report.stock_balance.stock_balance import (
	StockBalanceReport,
	filter_items_with_no_transactions,
)

ITEM_COLUMNS = {
	"name": pa.string(),
	"item_group": pa.string(),
	"stock_uom": pa.string(),
	"item_name": pa.string(),
	"has_serial_no": pa.int64(),
}
AMOUNT_FIELDS = (
	"actual_qty",
	"stock_value_difference",
	"qty_after_transaction",
	"stock_value",
	"valuation_rate",
)
LATEST_FIELDS = (
	"company",
	"item_group",
	"stock_uom",
	"item_name",
	"posting_date",
	"voucher_type",
	"voucher_no",
	"voucher_detail_no",
	"batch_no",
	"serial_no",
	"serial_and_batch_bundle",
	"is_adjustment_entry",
	*AMOUNT_FIELDS,
)
MOVEMENT_FIELDS = (
	"opening_qty",
	"in_qty",
	"out_qty",
	"bal_qty",
	"opening_val",
	"in_val",
	"out_val",
	"bal_val",
)

SEGMENTS_SQL = """
	WITH entries AS ({entries}),
	flagged AS (
		SELECT *,
			row_number() OVER (ORDER BY posting_datetime, creation) AS row_no,
			{dimension_key} AS dimension_key,
			posting_date < $from_date
				OR (voucher_type = 'Stock Entry' AND list_contains($opening_entries::VARCHAR[], voucher_no))
				OR (
					voucher_type = 'Stock Reconciliation'
					AND list_contains($opening_reconciliations::VARCHAR[], voucher_no)
				) AS is_opening,
			voucher_type = 'Stock Reconciliation'
				OR (actual_qty < 0 AND abs(actual_qty) < $unit)
				OR (stock_value_difference < 0 AND abs(stock_value_difference) < $unit) AS replay
		FROM entries
	),
	segments AS (
		SELECT *,
			sum(replay::INTEGER) OVER (PARTITION BY item_code, warehouse, dimension_key ORDER BY row_no) AS segment
		FROM flagged
	)
	SELECT item_code, warehouse, replay, min(row_no) AS row_no, {latest},
		sum(CASE WHEN is_opening THEN actual_qty ELSE 0 END) AS opening_qty,
		sum(CASE WHEN NOT is_opening AND actual_qty >= 0 THEN actual_qty ELSE 0 END) AS in_qty,
		sum(CASE WHEN NOT is_opening AND actual_qty < 0 THEN -actual_qty ELSE 0 END) AS out_qty,
		sum(actual_qty) AS bal_qty,
		sum(CASE WHEN is_opening THEN stock_value_difference ELSE 0 END) AS opening_val,
		sum(CASE WHEN NOT is_opening AND stock_value_difference >= 0 THEN stock_value_difference ELSE 0 END) AS in_val,
		sum(CASE WHEN NOT is_opening AND stock_value_difference < 0 THEN -stock_value_difference ELSE 0 END) AS out_val,
		sum(stock_value_difference) AS bal_val
	FROM segments
	GROUP BY item_code, warehouse, dimension_key, segment, replay
	ORDER BY row_no
"""

SERIAL_RECONCILIATIONS_SQL = """
	WITH entries AS ({entries})
	SELECT voucher_detail_no
	FROM entries
	WHERE voucher_type = 'Stock Reconciliation' AND has_serial_no = 1
	GROUP BY voucher_detail_no
	HAVING count(*) = 1
"""


def execute(filters):
	"""Ageing columns replay the ledger with live serial and batch lookups, which a snapshot cannot match."""
	if filters.get("show_stock_ageing_data"):
		frappe.throw(
			_(
				"Stock ageing data is not available from a snapshot. Uncheck {0}, or turn off {1} for this report."
			).format(frappe.bold(_("Show Stock Ageing Data")), frappe.bold(_("Snapshot Report")))
		)

	conn = get_latest_sync("Stock Ledger Entry")
	if not conn:
		frappe.throw(_("Stock Balance needs a DuckDB sync of Stock Ledger Entry"))

	try:
		return StockBalanceSnapshotReport(filters, conn).run()
	finally:
		conn.close()


class StockBalanceSnapshotReport(StockBalanceReport):
	"""Stock Balance with the ordinary movements between two balance resets summed in DuckDB.

	Resets and tiny negative amounts are replayed row by row with the live report's methods, which
	also serve everything that is not the ledger.
	"""

	def __init__(self, filters, conn):
		super().__init__(filters)
		self.conn = conn

	def prepare_item_warehouse_map_for_current_period(self):
		self.opening_vouchers = self.get_opening_vouchers()
		self.register_items()
		self.entries = self.get_entries()
		self.prepare_stock_reco_voucher_wise_count()

		for segment in self.run_sql(*self.get_segments()):
			self.apply_segment(segment)

		self.item_warehouse_map = filter_items_with_no_transactions(
			self.item_warehouse_map, self.float_precision, self.inventory_dimensions
		)

	def register_items(self):
		"""Items the live item filters allow, with the details the live ledger query joins in."""
		item = frappe.qb.DocType("Item")
		query = frappe.qb.from_(item).select(*(item[field] for field in ITEM_COLUMNS))
		rows = self.apply_items_filters(query, item).run(as_dict=True)
		self.conn.register(
			"snapshot_items", pa.Table.from_pylist(rows, schema=pa.schema(ITEM_COLUMNS.items()))
		)

	def get_warehouses(self):
		"""Warehouses the live warehouse filters allow, or None when no warehouse filter is set."""
		if not (self.filters.get("warehouse") or self.filters.get("warehouse_type")):
			return None

		warehouse = frappe.qb.DocType("Warehouse")
		ledger = frappe.qb.from_(warehouse).select(warehouse.name.as_("warehouse")).as_("ledger")
		query = self.apply_warehouse_filters(frappe.qb.from_(ledger).select(ledger.warehouse), ledger)
		return query.run(pluck=True)

	def get_entries(self):
		"""The ledger rows the live query reads, as DuckDB SQL and its parameters."""
		conditions, params = self.get_conditions()
		amounts = "".join(f", sle.{field}::DOUBLE AS {field}" for field in AMOUNT_FIELDS)
		dimensions = "".join(f', sle."{field}"' for field in self.inventory_dimensions)
		sql = f"""
			SELECT sle.item_code, sle.warehouse, sle.company, sle.posting_date, sle.posting_datetime,
				sle.creation, sle.voucher_type, sle.voucher_no, sle.voucher_detail_no, sle.batch_no,
				sle.serial_no, sle.serial_and_batch_bundle, sle.is_adjustment_entry, item.item_group,
				item.stock_uom, item.item_name, item.has_serial_no{amounts}{dimensions}
			FROM "tabStock Ledger Entry" sle
			JOIN snapshot_items item ON item.name = sle.item_code
			WHERE {conditions}"""
		return sql, params

	def get_conditions(self):
		conditions = ["sle.docstatus < 2", "sle.is_cancelled = 0", "sle.posting_date <= $to_date"]
		params = {"to_date": self.to_date}

		if not self.filters.ignore_closing_balance and self.start_from:
			conditions.append("sle.posting_date >= $start_from")
			params["start_from"] = getdate(self.start_from)

		if company := self.filters.get("company"):
			conditions.append("sle.company = $company")
			params["company"] = company

		if (warehouses := self.get_warehouses()) is not None:
			conditions.append("list_contains($warehouses::VARCHAR[], sle.warehouse)")
			params["warehouses"] = warehouses

		for index, field in enumerate(self.inventory_dimensions):
			if values := self.filters.get(field):
				conditions.append(f'list_contains($dimension_{index}::VARCHAR[], sle."{field}")')
				params[f"dimension_{index}"] = list(values)

		return " AND ".join(conditions), params

	def prepare_stock_reco_voucher_wise_count(self):
		self.stock_reco_voucher_wise_count = frappe._dict()
		sql, params = self.entries
		details = self.run_sql(SERIAL_RECONCILIATIONS_SQL.format(entries=sql), params)
		if not details:
			return

		for item in frappe.get_all(
			"Stock Reconciliation Item",
			filters={"name": ("in", [row.voucher_detail_no for row in details])},
			fields=["name", "current_qty", "qty"],
		):
			if item.qty and item.current_qty:
				self.stock_reco_voucher_wise_count[item.name] = item.current_qty

	def get_segments(self):
		sql, params = self.entries
		grouped = [f'"{field}"' for field in self.get_grouped_dimensions()]
		dimension_key = (
			f"list_filter([{', '.join(grouped)}], value -> coalesce(value, '') <> '')" if grouped else "NULL"
		)
		latest = ", ".join(
			f'arg_max_null("{field}", row_no) AS "{field}"'
			for field in (*LATEST_FIELDS, *self.inventory_dimensions)
		)
		query = SEGMENTS_SQL.format(entries=sql, dimension_key=dimension_key, latest=latest)
		return query, {
			**params,
			"from_date": self.from_date,
			"unit": 10**-self.float_precision,
			"opening_entries": self.opening_vouchers["Stock Entry"],
			"opening_reconciliations": self.opening_vouchers["Stock Reconciliation"],
		}

	def get_grouped_dimensions(self):
		"""Dimensions get_group_by_key() adds to the key, which drops their empty values."""
		return [
			field
			for field in self.inventory_dimensions
			if self.filters.get(field) or self.filters.get("show_dimension_wise_stock")
		]

	def apply_segment(self, segment):
		key = self.get_group_by_key(segment)
		if key not in self.item_warehouse_map:
			self.initialize_data(key, segment)

		if segment.replay:
			self.prepare_item_warehouse_map(segment, key)
			return

		balance = self.item_warehouse_map[key]
		for field in MOVEMENT_FIELDS:
			balance[field] += segment[field]
		balance.val_rate = segment.valuation_rate
		for field in self.inventory_dimensions:
			balance[field] = segment.get(field)

	def run_sql(self, sql, params):
		cursor = self.conn.execute(sql, params)
		columns = [column[0] for column in cursor.description]
		return [frappe._dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

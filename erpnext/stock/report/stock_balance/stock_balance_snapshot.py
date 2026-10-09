# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from itertools import batched
from operator import itemgetter

import frappe
import pyarrow as pa
from frappe import _
from frappe.database import get_duckdb
from frappe.database.duckdb.database import get_latest_complete_sync
from frappe.utils import getdate

from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import StockClosing
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
BATCH_SIZE = 1000
SEGMENT_DETAILS = ("company", "valuation_rate")

LEDGER_SQL = """
	CREATE TEMP TABLE ledger AS
	SELECT * EXCLUDE (posting_datetime, creation),
		row_number() OVER (ORDER BY posting_datetime, creation) AS row_no
	FROM (
		SELECT sle.item_code, sle.warehouse, sle.company, sle.actual_qty::DOUBLE AS actual_qty,
			sle.stock_value_difference::DOUBLE AS stock_value_difference,
			sle.valuation_rate::DOUBLE AS valuation_rate{dimensions},
			{dimension_key} AS dimension_key, sle.posting_datetime, sle.creation,
			sle.posting_date < $from_date
				OR (sle.voucher_type = 'Stock Entry' AND list_contains($opening_entries::VARCHAR[], sle.voucher_no))
				OR (
					sle.voucher_type = 'Stock Reconciliation'
					AND list_contains($opening_reconciliations::VARCHAR[], sle.voucher_no)
				) AS is_opening,
			sle.voucher_type = 'Stock Reconciliation'
				OR (sle.actual_qty < 0 AND abs(sle.actual_qty) < $unit)
				OR (sle.stock_value_difference < 0 AND abs(sle.stock_value_difference) < $unit) AS replay,
			CASE WHEN replay THEN sle.name END AS name
		FROM "tabStock Ledger Entry" sle
		JOIN snapshot_items item ON item.name = sle.item_code
		WHERE {conditions}
	)
"""

REPLAY_SQL = """
	CREATE TEMP TABLE replay AS
	SELECT ledger.* EXCLUDE (name), sle.posting_date, sle.voucher_type, sle.voucher_no, sle.voucher_detail_no,
		sle.batch_no, sle.serial_no, sle.serial_and_batch_bundle, sle.is_adjustment_entry,
		sle.qty_after_transaction::DOUBLE AS qty_after_transaction, sle.stock_value::DOUBLE AS stock_value,
		item.item_group, item.stock_uom, item.item_name, item.has_serial_no
	FROM ledger
	JOIN "tabStock Ledger Entry" sle ON sle.item_code = ledger.item_code AND sle.name = ledger.name
	JOIN snapshot_items item ON item.name = ledger.item_code
	WHERE ledger.replay
"""

SERIAL_RECONCILIATIONS_SQL = """
	SELECT voucher_detail_no
	FROM replay
	WHERE voucher_type = 'Stock Reconciliation' AND has_serial_no = 1
	GROUP BY voucher_detail_no
	HAVING count(*) = 1
"""

REPLAY_ROWS_SQL = "SELECT * FROM replay"

SEGMENTS_SQL = """
	SELECT segment.*, item.item_group, item.stock_uom, item.item_name
	FROM (
		SELECT item_code, warehouse, FALSE AS replay, min(row_no) AS row_no, {details},
			sum(CASE WHEN is_opening THEN actual_qty ELSE 0 END) AS opening_qty,
			sum(CASE WHEN NOT is_opening AND actual_qty >= 0 THEN actual_qty ELSE 0 END) AS in_qty,
			sum(CASE WHEN NOT is_opening AND actual_qty < 0 THEN -actual_qty ELSE 0 END) AS out_qty,
			sum(actual_qty) AS bal_qty,
			sum(CASE WHEN is_opening THEN stock_value_difference ELSE 0 END) AS opening_val,
			sum(CASE WHEN NOT is_opening AND stock_value_difference >= 0 THEN stock_value_difference ELSE 0 END) AS in_val,
			sum(CASE WHEN NOT is_opening AND stock_value_difference < 0 THEN -stock_value_difference ELSE 0 END) AS out_val,
			sum(stock_value_difference) AS bal_val
		FROM (
			SELECT *, count_if(replay) OVER (PARTITION BY item_code, warehouse, dimension_key ORDER BY row_no) AS segment
			FROM ledger
		)
		WHERE NOT replay
		GROUP BY item_code, warehouse, dimension_key, segment
	) segment
	JOIN snapshot_items item ON item.name = segment.item_code
"""


def execute(filters):
	"""Ageing columns replay the ledger with live serial and batch lookups, which a snapshot cannot match."""
	if filters.get("show_stock_ageing_data"):
		frappe.throw(
			_(
				"Stock ageing data is not available from a snapshot. Uncheck {0}, or turn off {1} for this report."
			).format(frappe.bold(_("Show Stock Ageing Data")), frappe.bold(_("Snapshot Report")))
		)

	sync = get_latest_complete_sync("Stock Ledger Entry")
	if not sync:
		frappe.throw(_("Stock Balance needs a DuckDB sync of Stock Ledger Entry"))

	conn = get_duckdb(True, sync.filename)
	try:
		return StockBalanceSnapshotReport(filters, conn, sync.creation).run()
	finally:
		conn.close()


class StockBalanceSnapshotReport(StockBalanceReport):
	"""Stock Balance with the ordinary movements between two balance resets summed in DuckDB.

	Resets and tiny negative amounts are replayed row by row with the live report's methods, which
	also serve everything that is not the ledger. Each segment's sum joins the running balance in one
	addition, while the live report adds row by row and accumulates float error. On large balances
	with many movements the last shown digits can therefore differ, the snapshot being nearer the
	exact total.
	"""

	def __init__(self, filters, conn, synced_at):
		super().__init__(filters)
		self.conn = conn
		self.synced_at = synced_at

	def get_entries_from_stock_closing_balance(self):
		"""A closing submitted after the sync can count entries the sync does not have, so the
		report then reads the whole ledger from the sync instead."""
		closing = StockClosing(self.filters.company, self.from_date, self.from_date).last_closing_balance
		if closing and frappe.db.get_value("Stock Closing Entry", closing.name, "modified") > self.synced_at:
			return []

		return super().get_entries_from_stock_closing_balance()

	def get_opening_vouchers(self):
		"""Opening vouchers cancelled after the sync still have ledger rows in it, so they count too."""
		vouchers = super().get_opening_vouchers()
		for voucher_type, opening in (
			("Stock Entry", {"is_opening": "Yes"}),
			("Stock Reconciliation", {"purpose": "Opening Stock"}),
		):
			vouchers[voucher_type] += frappe.get_all(
				voucher_type,
				filters={"docstatus": 2, "posting_date": ("<=", self.to_date), **opening},
				pluck="name",
			)

		return vouchers

	def prepare_item_warehouse_map_for_current_period(self):
		self.opening_vouchers = self.get_opening_vouchers()
		self.load_ledger()
		self.prepare_stock_reco_voucher_wise_count()

		changes = [*self.run_sql(REPLAY_ROWS_SQL), *self.run_sql(self.get_segments_sql())]
		for change in sorted(changes, key=itemgetter("row_no")):
			self.apply_change(change)

		self.item_warehouse_map = filter_items_with_no_transactions(
			self.item_warehouse_map, self.float_precision, self.inventory_dimensions
		)

	def load_ledger(self):
		"""Copy the ledger rows the live query reads into a temporary table, with the flags the
		report needs: whether a row counts as opening, and whether it is replayed row by row.

		Only the columns the segment sums need are kept for every row. The few replayed rows get
		the remaining columns of the live query in a second table."""
		conditions, params = self.get_conditions()
		self.register_items(conditions, params)
		grouped = ", ".join(f'sle."{field}"' for field in self.get_grouped_dimensions())
		sql = LEDGER_SQL.format(
			dimensions="".join(f', sle."{field}"' for field in self.inventory_dimensions),
			dimension_key=f"list_filter([{grouped}], value -> coalesce(value, '') <> '')"
			if grouped
			else "NULL",
			conditions=conditions,
		)
		self.conn.execute(
			sql,
			{
				**params,
				"from_date": self.from_date,
				"unit": 10**-self.float_precision,
				"opening_entries": self.opening_vouchers["Stock Entry"],
				"opening_reconciliations": self.opening_vouchers["Stock Reconciliation"],
			},
		)
		self.conn.execute(REPLAY_SQL)

	def register_items(self, conditions, params):
		"""Items with ledger rows under the report's filters that the live item filters allow, with
		the details the live ledger query joins in."""
		item = frappe.qb.DocType("Item")
		query = frappe.qb.from_(item).select(*(item[field] for field in ITEM_COLUMNS))
		query = self.apply_items_filters(query, item)
		rows = []
		for codes in batched(self.get_ledger_item_codes(conditions, params), BATCH_SIZE):
			rows += query.where(item.name.isin(codes)).run(as_dict=True)

		self.conn.register(
			"snapshot_items", pa.Table.from_pylist(rows, schema=pa.schema(ITEM_COLUMNS.items()))
		)

	def get_ledger_item_codes(self, conditions, params):
		sql = f'SELECT DISTINCT sle.item_code FROM "tabStock Ledger Entry" sle WHERE {conditions}'
		if item_codes := self.filters.get("item_code"):
			sql += " AND list_contains($item_codes::VARCHAR[], sle.item_code)"
			params = {**params, "item_codes": list(item_codes)}
		return [code for (code,) in self.conn.execute(sql, params).fetchall()]

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

	def get_warehouses(self):
		"""Warehouses the live warehouse filters allow, or None when no warehouse filter is set."""
		if not (self.filters.get("warehouse") or self.filters.get("warehouse_type")):
			return None

		warehouse = frappe.qb.DocType("Warehouse")
		ledger = frappe.qb.from_(warehouse).select(warehouse.name.as_("warehouse")).as_("ledger")
		query = self.apply_warehouse_filters(frappe.qb.from_(ledger).select(ledger.warehouse), ledger)
		return query.run(pluck=True)

	def get_grouped_dimensions(self):
		"""Dimensions get_group_by_key() adds to the key, which drops their empty values."""
		return [
			field
			for field in self.inventory_dimensions
			if self.filters.get(field) or self.filters.get("show_dimension_wise_stock")
		]

	def prepare_stock_reco_voucher_wise_count(self):
		self.stock_reco_voucher_wise_count = frappe._dict()
		details = self.run_sql(SERIAL_RECONCILIATIONS_SQL)
		if not details:
			return

		for item in frappe.get_all(
			"Stock Reconciliation Item",
			filters={"name": ("in", [row.voucher_detail_no for row in details])},
			fields=["name", "current_qty", "qty"],
		):
			if item.qty and item.current_qty:
				self.stock_reco_voucher_wise_count[item.name] = item.current_qty

	def get_segments_sql(self):
		fields = (*SEGMENT_DETAILS, *self.inventory_dimensions)
		return SEGMENTS_SQL.format(
			details=", ".join(f'arg_max_null("{field}", row_no) AS "{field}"' for field in fields)
		)

	def apply_change(self, change):
		key = self.get_group_by_key(change)
		if key not in self.item_warehouse_map:
			self.initialize_data(key, change)

		if change.replay:
			self.prepare_item_warehouse_map(change, key)
			return

		balance = self.item_warehouse_map[key]
		for field in MOVEMENT_FIELDS:
			balance[field] += change[field]
		balance.val_rate = change.valuation_rate
		for field in self.inventory_dimensions:
			balance[field] = change.get(field)

	def run_sql(self, sql, params=None):
		cursor = self.conn.execute(sql, params)
		columns = [column[0] for column in cursor.description]
		return [frappe._dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

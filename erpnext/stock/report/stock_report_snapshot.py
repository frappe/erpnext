# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import timedelta
from operator import itemgetter
from typing import NamedTuple

import frappe
from frappe import _
from frappe.query_builder.terms import NamedParameterWrapper

BATCH_SIZE = 1000


def run_stock_query(query, snapshot=None, **kwargs):
	if snapshot is not None:
		return snapshot.run(query, **kwargs)
	return query.run(**kwargs)


class StockReportSnapshot:
	"""Run stock queries against synced ledger entries and live supporting records.

	Only Stock Ledger Entry comes from the snapshot. Every doctype in LIVE_TABLES is read from
	the live database the first time a query needs it, so a report combines a frozen ledger with
	current master data. Those rows cover the ledger keys under the report's company, item and
	to_date filters, so a query that joins one of them must stay inside the same ledger scope.
	"""

	def __init__(self, report_name, filters=None):
		self.conn = self.get_connection(report_name)
		self.tables = {}
		self.filters = filters or {}

	def __enter__(self):
		return self

	def __exit__(self, *exc):
		self.conn.close()

	@staticmethod
	def get_connection(report_name):
		"""Open the latest submitted sync. An older complete sync is not served because the desk
		labels snapshot results with the latest submitted sync's timestamp."""
		sync = frappe.db.get_value(
			"DuckDB Sync",
			{"doc_type": "Stock Ledger Entry", "docstatus": 1},
			"name",
			order_by="creation desc",
		)
		if not sync or frappe.db.exists("DuckDB Sync Item", {"parent": sync, "synced": 0}):
			frappe.throw(
				_("{0} requires a completed Stock Ledger Entry sync to DuckDB").format(_(report_name))
			)
		return frappe.get_doc("DuckDB Sync", sync).get_duckdb_conn()

	def run(self, query, as_dict=False, as_iterator=False, pluck=False):
		sql, parameters = self.compile(query)
		cursor = self.conn.cursor()
		try:
			for name in self.get_referenced_tables(sql):
				cursor.register(name, self.get_table(name))
			cursor.execute(sql, parameters)
		except Exception:
			cursor.close()
			raise

		rows = self.iter_rows(cursor, as_dict, pluck)
		return rows if as_iterator else list(rows)

	@staticmethod
	def compile(query):
		parameters = DuckDBParameters()
		sql = query.get_sql(quote_char='"', alias_quote_char='"', param_wrapper=parameters)
		return sql, parameters.get_parameters()

	def get_referenced_tables(self, sql):
		names = dict.fromkeys([*self.tables, *(f"tab{doctype}" for doctype in LIVE_TABLES)])
		return [name for name in names if f'"{name}"' in sql]

	def register(self, name, rows, fields):
		"""Expose a lookup table built in Python to the queries that follow."""
		import pyarrow as pa

		self.tables[name] = pa.Table.from_pylist(rows, schema=arrow_schema(fields))

	def get_table(self, name):
		if name not in self.tables:
			self.tables[name] = self.build_live_table(name.removeprefix("tab"))
		return self.tables[name]

	def build_live_table(self, doctype):
		"""Read a supporting doctype in batches so a large table never lands in Python at once."""
		import pyarrow as pa

		table = LIVE_TABLES[doctype]
		schema = arrow_schema(table.fields)
		names = self.get_ledger_values(table.ledger_field, doctype)
		scope = (table.scope or {}).items()
		filters = {field: value for key, field in scope if (value := self.filters.get(key))}

		batches = []
		for offset in range(0, len(names), BATCH_SIZE):
			filters[table.link_field] = ("in", names[offset : offset + BATCH_SIZE])
			rows = frappe.get_all(doctype, filters=filters, fields=list(table.fields))
			batches.append(pa.RecordBatch.from_pylist(rows, schema=schema))

		# Explicit types also preserve the schema when a supporting table has no matching rows.
		return pa.Table.from_batches(batches, schema=schema)

	def get_ledger_values(self, field, doctype):
		"""Ledger keys a supporting table has to cover, under the report's own ledger scope."""
		ledger = frappe.qb.DocType("Stock Ledger Entry")
		query = frappe.qb.from_(ledger).select(ledger[field]).distinct().where(ledger[field].notnull())
		if field == "voucher_no":
			query = query.where(ledger.voucher_type == doctype)
		for key in ("company", "item_code"):
			if value := self.filters.get(key):
				values = value if isinstance(value, list | tuple) else [value]
				query = query.where(ledger[key].isin(values))
		if to_date := self.filters.get("to_date"):
			query = query.where(ledger.posting_date <= to_date)
		return [value for value in self.run(query, pluck=True) if value]

	@staticmethod
	def iter_rows(cursor, as_dict, pluck):
		columns = [column[0] for column in cursor.description]
		# Resolve conversions once per column, rather than inspecting every value in Python.
		converters = [
			(index, converter)
			for index, column in enumerate(cursor.description)
			if (converter := VALUE_CONVERTERS.get(column[1].id))
		]
		if pluck:
			shape = itemgetter(0)
		elif as_dict:

			def shape(row):
				return frappe._dict(zip(columns, row, strict=True))
		else:
			shape = tuple

		try:
			while rows := cursor.fetchmany(1000):
				for row in rows:
					if converters:
						row = list(row)
						for index, converter in converters:
							if row[index] is not None:
								row[index] = converter(row[index])
					yield shape(row)
		finally:
			cursor.close()


def arrow_schema(fields):
	import pyarrow as pa

	return pa.schema([(field, getattr(pa, dtype)()) for field, dtype in fields.items()])


def time_to_timedelta(value):
	return timedelta(
		hours=value.hour, minutes=value.minute, seconds=value.second, microseconds=value.microsecond
	)


VALUE_CONVERTERS = {"decimal": float, "time": time_to_timedelta, "time_tz": time_to_timedelta}


class DuckDBParameters(NamedParameterWrapper):
	def get_sql(self, param_value, **kwargs):
		key = f"param{len(self.parameters) + 1}"
		self.parameters[key] = param_value
		return f"${key}"


class LiveTable(NamedTuple):
	"""A supporting doctype read from the live database for the queries that need it.

	`ledger_field` is the Stock Ledger Entry column holding its keys and `link_field` the column
	those keys match. `scope` names report filters that narrow it further than those keys.
	"""

	ledger_field: str
	link_field: str
	fields: dict[str, str]
	scope: dict[str, str] | None = None


LIVE_TABLES = {
	"Item": LiveTable(
		"item_code",
		"name",
		{
			"name": "string",
			"item_code": "string",
			"item_name": "string",
			"description": "string",
			"stock_uom": "string",
			"brand": "string",
			"item_group": "string",
			"has_serial_no": "int64",
			"has_batch_no": "int64",
			"valuation_method": "string",
		},
	),
	"Warehouse": LiveTable(
		"warehouse",
		"name",
		{"name": "string", "lft": "int64", "rgt": "int64", "warehouse_type": "string"},
	),
	"Batch": LiveTable("batch_no", "name", {"name": "string", "use_batchwise_valuation": "int64"}),
	"Stock Reconciliation": LiveTable("voucher_no", "name", {"name": "string", "purpose": "string"}),
	"Serial and Batch Entry": LiveTable(
		"serial_and_batch_bundle",
		"parent",
		{
			"parent": "string",
			"qty": "float64",
			"stock_value_difference": "float64",
			"docstatus": "int64",
			"batch_no": "string",
		},
		{"batch_no": "batch_no"},
	),
}

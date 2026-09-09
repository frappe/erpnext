# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.query_builder.terms import NamedParameterWrapper


def run_stock_query(query, snapshot=None, **kwargs):
	if snapshot is not None:
		return snapshot.run(query, **kwargs)
	return query.run(**kwargs)


class StockReportSnapshot:
	"""Run stock queries against synced ledger entries and live supporting records."""

	def __init__(self, report_name, filters=None):
		self.conn = self.get_connection(report_name)
		self.live_tables = {}
		self.filters = filters or {}

	def __enter__(self):
		return self

	def __exit__(self, *exc):
		self.conn.close()

	@staticmethod
	def get_connection(report_name):
		sync = frappe.qb.DocType("DuckDB Sync")
		item = frappe.qb.DocType("DuckDB Sync Item")
		latest = (
			frappe.qb.from_(sync)
			.join(item)
			.on(item.parent == sync.name)
			.select(sync.name, item.synced)
			.where(
				(sync.doc_type == "Stock Ledger Entry")
				& (sync.docstatus == 1)
				& (item.table == "Stock Ledger Entry")
			)
			.orderby(sync.creation, order=frappe.qb.desc)
			.limit(1)
			.run(as_dict=True)
		)
		# The report's snapshot timestamp refers to the latest submitted sync.
		if not latest or not latest[0].synced:
			frappe.throw(
				_("{0} requires a completed Stock Ledger Entry sync to DuckDB").format(_(report_name))
			)
		return frappe.get_doc("DuckDB Sync", latest[0].name).get_duckdb_conn()

	def run(self, query, as_dict=False, as_iterator=False, pluck=False):
		sql, parameters = self.compile(query)
		cursor = self.conn.cursor()
		try:
			for doctype in LIVE_TABLES:
				table_name = f"tab{doctype}"
				if f'"{table_name}"' in sql:
					cursor.register(table_name, self.get_live_table(doctype))
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

	def get_live_table(self, doctype):
		import pyarrow as pa

		if doctype in self.live_tables:
			return self.live_tables[doctype]

		ledger_field, link_field, fields = LIVE_TABLES[doctype]
		names = self.get_ledger_values(ledger_field, doctype)
		rows = []
		for offset in range(0, len(names), 1000):
			rows.extend(
				frappe.get_all(
					doctype,
					filters={link_field: ("in", names[offset : offset + 1000])},
					fields=list(fields),
				)
			)

		# Explicit types also preserve the schema when a supporting table has no matching rows.
		schema = pa.schema([(field, getattr(pa, dtype)()) for field, dtype in fields.items()])
		self.live_tables[doctype] = pa.Table.from_pylist(rows, schema=schema)
		return self.live_tables[doctype]

	def get_ledger_values(self, field, doctype):
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
		try:
			while rows := cursor.fetchmany(1000):
				for row in rows:
					if converters:
						row = list(row)
						for index, converter in converters:
							if row[index] is not None:
								row[index] = converter(row[index])
					if pluck:
						yield row[0]
					elif as_dict:
						yield frappe._dict(zip(columns, row, strict=True))
					else:
						yield tuple(row)
		finally:
			cursor.close()


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


LIVE_TABLES = {
	"Item": (
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
	"Warehouse": (
		"warehouse",
		"name",
		{"name": "string", "lft": "int64", "rgt": "int64", "warehouse_type": "string"},
	),
	"Batch": ("batch_no", "name", {"name": "string", "use_batchwise_valuation": "int64"}),
	"Stock Reconciliation": ("voucher_no", "name", {"name": "string", "purpose": "string"}),
	"Serial and Batch Entry": (
		"serial_and_batch_bundle",
		"parent",
		{
			"parent": "string",
			"qty": "float64",
			"stock_value_difference": "float64",
			"docstatus": "int64",
			"batch_no": "string",
		},
	),
}

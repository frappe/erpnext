# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from random import Random
from unittest.mock import patch

import duckdb
import frappe
import pyarrow as pa

from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots
from erpnext.stock.report.stock_ageing.stock_ageing_snapshot import (
	DETAIL_FIELDS,
	FAST_KEYS,
)
from erpnext.stock.report.stock_report_snapshot import StockReportSnapshot
from erpnext.tests.utils import ERPNextTestSuite


class TestStockAgeingSnapshot(ERPNextTestSuite):
	def test_generated_histories_stay_pinned(self):
		"""The seeded histories are fixtures. A different sequence must fail here, not silently
		change what the FIFO tests cover."""
		digest = hashlib.sha256()
		for seed in range(20):
			for row in self.make_rows(seed):
				digest.update(json.dumps(row, default=str, sort_keys=True).encode())

		self.assertEqual(
			digest.hexdigest(), "c0d6222b7c07fb59a5f43f7186e2236ae574f83646453a11f1bd6321992abf33"
		)

	def test_randomized_fifo_layers_match_replay(self):
		for seed in range(20):
			with self.subTest(seed=seed):
				rows = self.make_rows(seed)
				self.assertEqual(self.calculate(rows), self.replay(rows))

	def test_exact_exhaustion_discards_residual_value(self):
		rows = self.make_rows(0)[:7]
		for row, qty, value in zip(
			rows, (10, 5, -10, -2, 4, -7, 3), (100, 200, -90, -30, 100, -300, 75), strict=True
		):
			row.update(name="Item", warehouse="Warehouse", actual_qty=qty, stock_value_difference=value)
		self.assertEqual(self.calculate(rows), self.replay(rows))

	def test_moving_average_layers_match_replay(self):
		rows = self.make_rows(2)
		self.assertEqual(self.calculate(rows, "Moving Average"), self.replay(rows, "Moving Average"))

	def test_fractional_group_does_not_disable_other_groups(self):
		rows = self.make_rows(5)
		for row in rows:
			row.name += "' quoted item"
			row.warehouse += '" quoted warehouse'
		rows[0].stock_value_difference = 0.1
		self.assertEqual(self.calculate(rows), self.replay(rows))

	def test_unsupported_histories_use_replay(self):
		for update in (
			{"actual_qty": -100},
			{"actual_qty": 0.1},
			{"stock_value_difference": 0.1},
			{"voucher_type": "Stock Reconciliation"},
			{"serial_no": "Serial"},
			{"batch_no": "Batch"},
			{"serial_and_batch_bundle": "Bundle"},
			{"has_serial_no": 1},
			{"has_batch_no": 1},
		):
			with self.subTest(update=update):
				rows = self.make_rows(0)
				for row in rows:
					row.update(name="Item", warehouse="Warehouse")
				rows[0].update(update)
				self.assertIsNone(self.calculate(rows))
		self.assertIsNone(self.calculate(self.make_rows(0), "LIFO"))
		rows = self.make_rows(0)
		for row in rows:
			row.stock_value_difference = 999999999999
		self.assertIsNone(self.calculate(rows))

	def test_reused_voucher_and_ambiguous_order_use_replay(self):
		for fields in (("voucher_no",), ("posting_datetime", "creation")):
			rows = self.make_rows(0)
			for row in rows:
				row.update(name="Item", warehouse="Warehouse")
			other = next(
				row for row in rows[1:] if (row.name, row.warehouse) == (rows[0].name, rows[0].warehouse)
			)
			for field in fields:
				other[field] = rows[0][field]
			self.assertIsNone(self.calculate(rows))

	def test_split_does_not_bind_a_parameter_per_group(self):
		rows = self.make_rows(5)
		rows[0].stock_value_difference = 0.1
		counts = self.count_split_parameters(rows)
		self.assertTrue(counts)
		self.assertEqual(set(counts), {0})

	def count_split_parameters(self, rows):
		"""Parameters bound by the queries that split aggregated groups from replayed ones."""
		counts = []
		compile_query = StockReportSnapshot.compile

		def record(query):
			sql, parameters = compile_query(query)
			if FAST_KEYS in sql:
				counts.append(len(parameters))
			return sql, parameters

		with patch.object(StockReportSnapshot, "compile", staticmethod(record)):
			self.assertEqual(self.calculate(rows), self.replay(rows))

		return counts

	def calculate(self, rows, method="FIFO"):
		fifo = self.make_fifo(rows, method)
		with duckdb.connect(":memory:") as conn:
			conn.from_arrow(self.as_arrow(rows)).create("tabStock Ledger Entry")
			snapshot = StockReportSnapshot.__new__(StockReportSnapshot)
			snapshot.conn, snapshot.filters, snapshot.tables = conn, {}, {}
			fifo.snapshot = snapshot
			ledger = frappe.qb.DocType("Stock Ledger Entry")
			query = frappe.qb.from_(ledger).select(*(ledger[field] for field in DETAIL_FIELDS))
			with patch.object(
				fifo,
				"_get_stock_ledger_query",
				side_effect=lambda ordered=True: query.orderby(ledger.posting_datetime, ledger.creation)
				if ordered
				else query,
			):
				if fifo._generate_from_snapshot({}, {}):
					fifo._recompute_moving_average_slots()
					return fifo.item_details

	def replay(self, rows, method="FIFO"):
		fifo = self.make_fifo(rows, method)
		for row in rows:
			fifo._process_stock_ledger_entry(
				frappe._dict({field: row[field] for field in DETAIL_FIELDS}), {}, {}
			)
		fifo._recompute_moving_average_slots()
		return fifo.item_details

	def make_fifo(self, rows, method):
		fifo = FIFOSlots(frappe._dict(company="_Test Company", to_date="2026-12-31"), deepcopy(rows))
		fifo.valuation_method_by_item = {row.name: method for row in rows}
		fifo.stock_reco_voucher_wise_count = {}
		fifo.float_precision = 3
		return fifo

	def make_rows(self, seed):
		random = Random(seed)
		balances, rows = {}, []
		for index in range(120):
			item, warehouse = random.choice(("C", "A", "B")), random.choice(("W2", "W1"))
			key = (item, warehouse)
			balance = balances.get(key, 0)
			qty = random.randint(1, 40) / 4
			if balance and random.random() < 0.6:
				qty = -min(qty, balance)
			balances[key] = balance + qty
			date = datetime(2026, 1, 1) + timedelta(hours=index)
			row = frappe._dict({field: None for field in DETAIL_FIELDS})
			row.update(
				name=item,
				warehouse=warehouse,
				item_name=item,
				item_group="Products",
				brand="Brand",
				description=item,
				stock_uom="Nos",
				has_serial_no=0,
				has_batch_no=0,
				actual_qty=qty,
				qty_after_transaction=balances[key],
				valuation_rate=random.randint(1, 100) / 4,
				stock_value_difference=random.randint(-400, 400) / 4,
				posting_date=date.date(),
				posting_datetime=date,
				creation=date,
				voucher_no=f"Voucher {index}",
				voucher_detail_no=f"Detail {index}",
				voucher_type="Stock Entry",
			)
			rows.append(row)
		return rows

	def as_arrow(self, rows):
		rows = deepcopy(rows)
		for row in rows:
			row.item_code = row.name
		decimals = {"actual_qty", "qty_after_transaction", "stock_value_difference", "valuation_rate"}
		fields = []
		for field in (*DETAIL_FIELDS, "posting_datetime", "creation", "item_code"):
			if field in decimals:
				dtype = pa.decimal128(21, 9)
				for row in rows:
					row[field] = Decimal(str(row[field])) if row[field] is not None else None
			elif field in ("posting_datetime", "creation"):
				dtype = pa.timestamp("us")
			elif field == "posting_date":
				dtype = pa.date32()
			elif field in ("has_serial_no", "has_batch_no"):
				dtype = pa.int64()
			else:
				dtype = pa.string()
			fields.append((field, dtype))
		return pa.Table.from_pylist(rows, schema=pa.schema(fields))

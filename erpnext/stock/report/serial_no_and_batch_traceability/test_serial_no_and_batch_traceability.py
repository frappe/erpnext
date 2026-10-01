# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_serial_nos_from_bundle,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.serial_no_and_batch_traceability.serial_no_and_batch_traceability import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialNoAndBatchTraceability(ERPNextTestSuite):
	def setUp(self):
		self.raw_item = make_item(
			"_Test Traceability Raw Item",
			{"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "TTRI-.#####"},
		).name
		self.fg_item = make_item("_Test Traceability FG Item", {"is_stock_item": 1, "has_serial_no": 1}).name

		self.receipt = make_stock_entry(
			item_code=self.raw_item, target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)
		self.serial_no = get_serial_nos_from_bundle(self.receipt.items[0].serial_and_batch_bundle)[0]

	def test_backward_trace_of_serial_no_moved_by_repack(self):
		repack = self.make_repack(self.raw_item, self.fg_item)

		self.assertEqual(
			self.get_backward_trace(),
			[(self.fg_item, repack.name, 0), (self.raw_item, self.receipt.name, 1)],
		)

	def test_backward_trace_of_serial_no_moved_back_by_repack(self):
		repack = self.make_repack(self.raw_item, self.fg_item)
		repack_back = self.make_repack(self.fg_item, self.raw_item)

		self.assertEqual(
			self.get_backward_trace(),
			[
				(self.raw_item, repack_back.name, 0),
				(self.fg_item, repack.name, 1),
				(self.raw_item, self.receipt.name, 2),
			],
		)

	def test_backward_trace_of_serial_no_moved_at_same_posting_time(self):
		"""Entries with the same posting time follow the ledger order."""
		same_time = {"posting_date": self.receipt.posting_date, "posting_time": self.receipt.posting_time}
		first_repack = self.make_repack(self.raw_item, self.fg_item, **same_time)
		second_repack = self.make_repack(self.fg_item, self.raw_item, **same_time)
		third_repack = self.make_repack(self.raw_item, self.fg_item, **same_time)

		self.assertEqual(
			self.get_backward_trace(),
			[
				(self.fg_item, third_repack.name, 0),
				(self.raw_item, second_repack.name, 1),
				(self.fg_item, first_repack.name, 2),
				(self.raw_item, self.receipt.name, 3),
			],
		)

	def make_repack(self, from_item, to_item, **kwargs):
		"""Repack the serial no from one item to another, in the same warehouse."""
		repack = make_stock_entry(
			**kwargs,
			item_code=from_item,
			source="_Test Warehouse - _TC",
			qty=1,
			purpose="Repack",
			serial_no=self.serial_no,
			use_serial_batch_fields=1,
			do_not_save=True,
		)
		repack.append(
			"items",
			{
				"item_code": to_item,
				"t_warehouse": "_Test Warehouse - _TC",
				"qty": 1,
				"conversion_factor": 1.0,
				"serial_no": self.serial_no,
				"use_serial_batch_fields": 1,
			},
		)
		repack.save()
		repack.submit()
		return repack

	def get_backward_trace(self):
		_columns, data = execute(
			frappe._dict({"serial_nos": [self.serial_no], "traceability_direction": "Backward"})
		)
		return [(row["item_code"], row["reference_name"], row["indent"]) for row in data if row]

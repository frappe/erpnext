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
	def test_backward_trace_of_serial_no_moved_by_repack(self):
		raw_item = make_item(
			"_Test Traceability Raw Item",
			{"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "TTRI-.#####"},
		).name
		fg_item = make_item("_Test Traceability FG Item", {"is_stock_item": 1, "has_serial_no": 1}).name

		receipt = make_stock_entry(item_code=raw_item, target="_Test Warehouse - _TC", qty=1, basic_rate=100)
		serial_no = get_serial_nos_from_bundle(receipt.items[0].serial_and_batch_bundle)[0]

		repack = make_stock_entry(
			item_code=raw_item,
			source="_Test Warehouse - _TC",
			qty=1,
			purpose="Repack",
			serial_no=serial_no,
			use_serial_batch_fields=1,
			do_not_save=True,
		)
		repack.append(
			"items",
			{
				"item_code": fg_item,
				"t_warehouse": "_Test Warehouse 1 - _TC",
				"qty": 1,
				"conversion_factor": 1.0,
				"serial_no": serial_no,
				"use_serial_batch_fields": 1,
			},
		)
		repack.save()
		repack.submit()

		_columns, data = execute(
			frappe._dict({"serial_nos": [serial_no], "traceability_direction": "Backward"})
		)
		rows = [(row["item_code"], row["reference_name"], row["indent"], row["qty"]) for row in data if row]

		self.assertEqual(rows, [(fg_item, repack.name, 0, 1), (raw_item, receipt.name, 1, 1)])

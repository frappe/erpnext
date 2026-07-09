# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.incorrect_serial_and_batch_bundle.incorrect_serial_and_batch_bundle import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestIncorrectSerialAndBatchBundle(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company"})
		filters.update(extra)
		return execute(filters)[1]

	def test_healthy_bundles_not_flagged(self):
		batch_item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "ISBB-.#####",
			}
		).name
		serial_item = "_Test Serialized Item With Series"

		make_stock_entry(
			item_code=batch_item,
			qty=10,
			rate=100,
			to_warehouse="Stores - _TC",
			posting_date="2026-06-01",
		)
		make_stock_entry(
			item_code=serial_item,
			qty=3,
			rate=100,
			to_warehouse="Stores - _TC",
			posting_date="2026-06-01",
		)

		data = self.run_report()

		bundles = frappe.get_all(
			"Serial and Batch Bundle",
			filters={"item_code": ["in", [batch_item, serial_item]]},
			pluck="name",
		)

		flagged_names = {row.get("name") for row in data}
		self.assertFalse(
			flagged_names.intersection(bundles),
			msg="Healthy serial/batch bundles should not be flagged as incorrect.",
		)

	def test_unlinked_bundle_is_flagged(self):
		# an actual incorrect state: a submitted Serial and Batch Bundle left without any linking
		# Stock Ledger Entry (e.g. the SLE was purged but the bundle survived)
		batch_item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "ISBB-ORPHAN-.#####",
			}
		).name

		entry = make_stock_entry(
			item_code=batch_item, qty=5, rate=100, to_warehouse="Stores - _TC", posting_date="2026-06-01"
		)
		bundle = frappe.db.get_value("Serial and Batch Bundle", {"voucher_no": entry.name}, "name")
		self.assertTrue(bundle)

		# orphan the bundle: drop the Stock Ledger Entry that referenced it
		frappe.db.delete("Stock Ledger Entry", {"serial_and_batch_bundle": bundle})

		flagged = {row.get("name"): row for row in self.run_report()}
		self.assertIn(bundle, flagged)
		self.assertEqual(flagged[bundle]["is_cancelled"], 0)

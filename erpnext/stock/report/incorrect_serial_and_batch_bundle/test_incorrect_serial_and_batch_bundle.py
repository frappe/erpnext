# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import POSInvoiceTestMixin, create_pos_invoice
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

	def test_fix_leaves_draft_bundles_alone(self):
		from erpnext.stock.report.incorrect_serial_and_batch_bundle.incorrect_serial_and_batch_bundle import (
			fix_sabb_entries,
		)

		batch_item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1, "create_new_batch": 1}).name
		entry = make_stock_entry(item_code=batch_item, qty=5, rate=100, to_warehouse="Stores - _TC")
		bundle = frappe.db.get_value("Serial and Batch Bundle", {"voucher_no": entry.name}, "name")
		frappe.db.delete("Stock Ledger Entry", {"serial_and_batch_bundle": bundle})
		frappe.db.set_value("Serial and Batch Bundle", bundle, "docstatus", 0)

		fix_sabb_entries([{"name": bundle}])

		self.assertEqual(
			frappe.db.get_value("Serial and Batch Bundle", bundle, ["docstatus", "is_cancelled"]), (0, 0)
		)

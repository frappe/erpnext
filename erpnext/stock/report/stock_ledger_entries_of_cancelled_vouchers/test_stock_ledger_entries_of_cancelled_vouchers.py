# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_ledger_entries_of_cancelled_vouchers.stock_ledger_entries_of_cancelled_vouchers import (
	execute,
	fix_uncancelled_entries,
)


class TestStockLedgerEntriesOfCancelledVouchers(FrappeTestCase):
	def run_report(self):
		return execute(frappe._dict({"company": "_Test Company", "voucher_type": "Stock Entry"}))[1]

	def test_uncancelled_sle_of_cancelled_voucher(self):
		batch_item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "USLE-.#####",
			}
		).name

		entry = make_stock_entry(
			item_code=batch_item, qty=5, rate=100, to_warehouse="Stores - _TC", posting_date="2026-06-01"
		)
		self.assertFalse([d for d in self.run_report() if d.voucher_no == entry.name])

		entry.cancel()

		sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": entry.name, "actual_qty": 5})
		bundle = frappe.db.get_value("Serial and Batch Bundle", {"voucher_no": entry.name})

		# simulate a repost that wrote back the in-memory (uncancelled) state after the cancel
		frappe.db.set_value("Stock Ledger Entry", sle, "is_cancelled", 0)
		frappe.db.set_value("Serial and Batch Bundle", bundle, {"is_cancelled": 0, "docstatus": 1})
		frappe.db.set_value("Serial and Batch Entry", {"parent": bundle}, "docstatus", 1)

		rows = [d for d in self.run_report() if d.voucher_no == entry.name]
		self.assertEqual([(d.name, d.serial_and_batch_bundle) for d in rows], [(sle, bundle)])

		fix_uncancelled_entries(rows)

		self.assertFalse([d for d in self.run_report() if d.voucher_no == entry.name])
		self.assertEqual(frappe.db.get_value("Stock Ledger Entry", sle, "is_cancelled"), 1)
		self.assertEqual(
			frappe.db.get_value("Serial and Batch Bundle", bundle, ["is_cancelled", "docstatus"]), (1, 2)
		)
		self.assertFalse(
			frappe.db.exists("Serial and Batch Entry", {"parent": bundle, "docstatus": ["!=", 2]})
		)

	def test_fix_reposts_future_entries(self):
		item = make_item(properties={"is_stock_item": 1}).name
		warehouse = "Stores - _TC"

		make_stock_entry(item_code=item, qty=10, rate=100, to_warehouse=warehouse, posting_date="2026-06-01")
		entry = make_stock_entry(
			item_code=item, qty=5, rate=200, to_warehouse=warehouse, posting_date="2026-06-02"
		)
		future_entry = make_stock_entry(
			item_code=item, qty=3, rate=100, to_warehouse=warehouse, posting_date="2026-06-03"
		)
		entry.cancel()

		# simulate a repost that wrote back the uncancelled entry and kept it in the future balances
		sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": entry.name, "actual_qty": 5})
		future_sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": future_entry.name})
		frappe.db.set_value("Stock Ledger Entry", sle, "is_cancelled", 0)
		frappe.db.set_value(
			"Stock Ledger Entry", future_sle, {"qty_after_transaction": 18, "stock_value": 2300}
		)
		frappe.db.set_value("Bin", {"item_code": item, "warehouse": warehouse}, "actual_qty", 18)

		rows = [d for d in self.run_report() if d.voucher_no == entry.name]
		self.assertEqual([d.name for d in rows], [sle])

		fix_uncancelled_entries(rows)

		self.assertTrue(
			frappe.db.exists(
				"Repost Item Valuation",
				{"based_on": "Item and Warehouse", "item_code": item, "warehouse": warehouse, "docstatus": 1},
			)
		)
		self.assertEqual(
			frappe.db.get_value("Stock Ledger Entry", future_sle, ["qty_after_transaction", "stock_value"]),
			(13, 1300),
		)
		self.assertEqual(
			frappe.db.get_value("Bin", {"item_code": item, "warehouse": warehouse}, "actual_qty"), 13
		)

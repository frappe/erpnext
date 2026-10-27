# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.incorrect_balance_qty_after_transaction.incorrect_balance_qty_after_transaction import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"
COMPANY = "_Test Company"


class TestIncorrectBalanceQtyAfterTransaction(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": COMPANY, "warehouse": WAREHOUSE})
		filters.update(extra)
		return execute(filters)[1]

	def test_healthy_stock_not_flagged(self):
		item = "_Test Item"
		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=10, rate=100, posting_date="2026-06-01")
		make_stock_entry(item_code=item, from_warehouse=WAREHOUSE, qty=4, rate=100, posting_date="2026-06-02")

		data = self.run_report(item_code=item)
		flagged = [row for row in data if row.get("item_code") == item]
		self.assertEqual(flagged, [])

	def test_inconsistent_balance_qty_is_flagged(self):
		# a unique item keeps this SLE the only ledger entry for the item/warehouse
		item = make_item(properties={"is_stock_item": 1}).name
		entry = make_stock_entry(
			item_code=item, to_warehouse=WAREHOUSE, qty=10, rate=100, posting_date="2026-06-01"
		)

		# Corrupt the running balance so it no longer matches the cumulative actual_qty --
		# exactly the inconsistency this report exists to detect. set_value bypasses the
		# ledger recompute that would otherwise keep the two in sync.
		sle_name = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": entry.name, "item_code": item, "warehouse": WAREHOUSE},
			"name",
		)
		frappe.db.set_value("Stock Ledger Entry", sle_name, "qty_after_transaction", 5)

		flagged = [row for row in self.run_report(item_code=item) if row.get("name") == sle_name]
		self.assertEqual(len(flagged), 1, "The tampered stock ledger entry should be flagged")
		row = flagged[0]
		self.assertEqual(row["expected_balance_qty"], 10)  # cumulative actual_qty
		self.assertEqual(row["qty_after_transaction"], 5)  # tampered balance
		self.assertEqual(row["differnce"], 5)

	def test_sequence_of_movements_not_flagged(self):
		item = "_Test Item 2"
		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=20, rate=50, posting_date="2026-06-01")
		make_stock_entry(item_code=item, from_warehouse=WAREHOUSE, qty=5, rate=50, posting_date="2026-06-02")
		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=8, rate=50, posting_date="2026-06-03")
		make_stock_entry(item_code=item, from_warehouse=WAREHOUSE, qty=3, rate=50, posting_date="2026-06-04")

		data = self.run_report(item_code=item)
		flagged = [row for row in data if row.get("item_code") == item]
		self.assertEqual(flagged, [])

	def test_difference_below_half_a_unit_is_flagged(self):
		item = make_item(properties={"is_stock_item": 1, "stock_uom": "Kg"}).name
		entry = make_stock_entry(
			item_code=item, to_warehouse=WAREHOUSE, qty=10.5, rate=100, posting_date="2026-06-01"
		)
		sle_name = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": entry.name}, "name")
		frappe.db.set_value("Stock Ledger Entry", sle_name, "qty_after_transaction", 10.9)

		flagged = [row for row in self.run_report(item_code=item) if row.get("name") == sle_name]

		self.assertEqual(len(flagged), 1)
		self.assertAlmostEqual(flagged[0]["differnce"], 0.4)

	def test_balance_rounded_like_the_ledger_is_not_flagged_without_precision(self):
		self.addCleanup(frappe.db.set_default, "float_precision", frappe.db.get_default("float_precision"))
		self.addCleanup(
			frappe.db.set_single_value,
			"System Settings",
			"float_precision",
			frappe.db.get_single_value("System Settings", "float_precision"),
		)
		frappe.db.set_default("float_precision", None)
		frappe.db.set_single_value("System Settings", "float_precision", "")
		item = make_item(properties={"is_stock_item": 1, "stock_uom": "Kg"}).name
		entry = make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=1, rate=100)
		sle_name = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": entry.name}, "name")
		frappe.db.set_value(
			"Stock Ledger Entry", sle_name, {"actual_qty": 1.234, "qty_after_transaction": 1.23}
		)

		self.assertEqual(self.run_report(item_code=item), [])

	def test_reconciliation_entry_is_checked_against_its_reconciled_qty(self):
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=10, rate=100, posting_date="2026-06-01")
		reconciliation = create_stock_reconciliation(
			item_code=item, warehouse=WAREHOUSE, qty=7, rate=100, posting_date="2026-06-02"
		)
		sle_name = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": reconciliation.name}, "name")
		frappe.db.set_value("Stock Ledger Entry", sle_name, "qty_after_transaction", 9)

		flagged = [row for row in self.run_report(item_code=item) if row.get("name") == sle_name]

		self.assertEqual([(row["expected_balance_qty"], row["differnce"]) for row in flagged], [(7, 2)])

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_ledger_entries_of_cancelled_vouchers.stock_ledger_entries_of_cancelled_vouchers import (
	execute,
	fix_uncancelled_entries,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestStockLedgerEntriesOfCancelledVouchers(ERPNextTestSuite):
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
		frappe.db.set_value("Serial and Batch Entry", {"parent": bundle}, {"is_cancelled": 0, "docstatus": 1})

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

	def test_fix_requires_stock_manager(self):
		frappe.set_user("Guest")
		try:
			self.assertRaises(frappe.PermissionError, fix_uncancelled_entries, [])
		finally:
			frappe.set_user("Administrator")

	def test_stock_manager_can_run_report_and_fix(self):
		item = make_item(properties={"is_stock_item": 1}).name
		entry = make_stock_entry(
			item_code=item, qty=5, rate=100, to_warehouse="Stores - _TC", posting_date="2026-06-01"
		)
		entry.cancel()

		sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": entry.name, "actual_qty": 5})
		frappe.db.set_value("Stock Ledger Entry", sle, "is_cancelled", 0)

		frappe.set_user(make_stock_manager("sle-cancelled-voucher-sm@example.com"))
		try:
			rows = [d for d in self.run_report() if d.voucher_no == entry.name]
			self.assertEqual([d.name for d in rows], [sle])
			fix_uncancelled_entries(rows)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(frappe.db.get_value("Stock Ledger Entry", sle, "is_cancelled"), 1)

	def test_company_user_permission(self):
		item = make_item(properties={"is_stock_item": 1}).name
		entry = make_stock_entry(
			item_code=item, qty=5, rate=100, to_warehouse="Stores - _TC", posting_date="2026-06-01"
		)
		entry.cancel()

		frappe.set_user(
			make_stock_manager("sle-cancelled-voucher-restricted@example.com", company="_Test Company 1")
		)
		try:
			self.assertRaises(frappe.PermissionError, self.run_report)
			self.assertRaises(
				frappe.PermissionError,
				fix_uncancelled_entries,
				[{"voucher_type": "Stock Entry", "voucher_no": entry.name}],
			)
		finally:
			frappe.set_user("Administrator")

	def test_company_is_mandatory(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict())


def make_stock_manager(user, company=None):
	from frappe.permissions import add_user_permission

	if not frappe.db.exists("User", user):
		frappe.get_doc(
			{"doctype": "User", "email": user, "first_name": "Stock Manager", "send_welcome_email": 0}
		).insert(ignore_permissions=True)

	frappe.get_doc("User", user).add_roles("Stock Manager")
	if company:
		add_user_permission("Company", company, user)

	return user

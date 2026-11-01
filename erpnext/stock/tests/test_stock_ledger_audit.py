# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.stock_ledger_audit import StockLedgerAudit, audit_stock_ledger_entries

COMPANY = "_Test Company"
WAREHOUSE = "Stores - _TC"


class TestStockLedgerAudit(FrappeTestCase):
	def setUp(self):
		self.from_date = get_fiscal_year(today(), company=COMPANY)[1]
		self.item = make_item(properties={"valuation_method": "Moving Average"}).name

	def make_receipt(self, qty, rate, posting_date=None):
		entry = make_stock_entry(
			item_code=self.item,
			to_warehouse=WAREHOUSE,
			qty=qty,
			rate=rate,
			posting_date=posting_date or today(),
		)
		return frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": entry.name, "is_cancelled": 0}, "name"
		)

	def make_incorrect_entry(self):
		self.make_receipt(10, 100)
		sle = self.make_receipt(5, 120)
		frappe.db.set_value("Stock Ledger Entry", sle, {"stock_value": 1500, "valuation_rate": 100})
		return sle

	def run_audit(self):
		StockLedgerAudit(COMPANY, self.from_date).audit(self.item, WAREHOUSE)

	def get_scheduler_reposts(self):
		return frappe.get_all(
			"Repost Item Valuation",
			filters={"item_code": self.item, "warehouse": WAREHOUSE, "created_by_scheduler": 1},
			fields=["name", "posting_date", "posting_time", "status"],
		)

	def test_incorrect_entry_is_reposted_from_its_posting_time(self):
		sle = self.make_incorrect_entry()

		self.run_audit()

		reposts = self.get_scheduler_reposts()
		posting = frappe.db.get_value("Stock Ledger Entry", sle, ["posting_date", "posting_time"])
		self.assertEqual(len(reposts), 1)
		self.assertEqual((reposts[0].posting_date, reposts[0].posting_time), posting)
		self.assertEqual(reposts[0].status, "Completed")
		self.assertEqual(frappe.db.get_value("Stock Ledger Entry", sle, "stock_value"), 1600)

	def test_correct_entries_are_not_reposted(self):
		self.make_receipt(10, 100)
		self.make_receipt(5, 120)

		self.run_audit()

		self.assertFalse(self.get_scheduler_reposts())

	def test_entries_before_fiscal_year_are_not_audited(self):
		sle = self.make_receipt(10, 100, posting_date=add_days(self.from_date, -1))
		frappe.db.set_value("Stock Ledger Entry", sle, {"stock_value": 900, "valuation_rate": 90})
		self.make_receipt(5, 120)

		self.run_audit()

		self.assertFalse(self.get_scheduler_reposts())

	def test_item_warehouse_with_pending_repost_is_skipped(self):
		self.make_incorrect_entry()
		repost = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Item and Warehouse",
				"item_code": self.item,
				"warehouse": WAREHOUSE,
				"posting_date": today(),
			}
		)
		repost.flags.dont_run_in_test = True
		repost.submit()

		self.run_audit()

		self.assertFalse(self.get_scheduler_reposts())

	@patch.dict(frappe.flags, {"dont_execute_stock_reposts": True})
	def test_failed_scheduler_repost_is_not_created_again(self):
		self.make_incorrect_entry()
		self.run_audit()
		repost = self.get_scheduler_reposts()[0]
		frappe.db.set_value("Repost Item Valuation", repost.name, "status", "Failed")

		self.run_audit()

		self.assertEqual(len(self.get_scheduler_reposts()), 1)

	def test_repost_that_cannot_be_created_is_logged(self):
		sle = self.make_incorrect_entry()
		self.addCleanup(frappe.db.set_single_value, "Accounts Settings", "acc_frozen_upto", None)
		frappe.db.set_single_value(
			"Accounts Settings", {"acc_frozen_upto": today(), "frozen_accounts_modifier": None}
		)

		with patch("frappe.log_error") as log_error:
			self.run_audit()

		self.assertFalse(self.get_scheduler_reposts())
		self.assertEqual(log_error.call_args.kwargs["reference_name"], sle)

	def test_audit_is_queued_for_every_company(self):
		with patch("frappe.enqueue") as enqueue:
			audit_stock_ledger_entries()

		self.assertEqual(enqueue.call_count, frappe.db.count("Company"))

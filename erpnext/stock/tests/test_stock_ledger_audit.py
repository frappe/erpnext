# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, get_datetime, now_datetime, today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.stock_ledger_audit import (
	RECENT_CHANGES_DAYS,
	StockLedgerAudit,
	audit_recent_stock_ledger_entries,
	audit_stock_ledger_entries,
)
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "Stores - _TC"


class TestStockLedgerAudit(ERPNextTestSuite):
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

	def make_repost(self, posting_date, run=True):
		repost = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Item and Warehouse",
				"item_code": self.item,
				"warehouse": WAREHOUSE,
				"posting_date": posting_date,
			}
		)
		repost.flags.dont_run_in_test = not run
		return repost.submit()

	def move_entries_before_recent_days(self):
		changed_on = add_days(now_datetime(), -RECENT_CHANGES_DAYS - 1)
		sle = frappe.qb.DocType("Stock Ledger Entry")
		(
			frappe.qb.update(sle)
			.set(sle.creation, changed_on)
			.set(sle.modified, changed_on)
			.where(sle.item_code == self.item)
		).run()

	def move_reposts_before_recent_days(self):
		changed_on = add_days(now_datetime(), -RECENT_CHANGES_DAYS - 1)
		repost = frappe.qb.DocType("Repost Item Valuation")
		sle = frappe.qb.DocType("Stock Ledger Entry")
		vouchers = frappe.qb.from_(sle).select(sle.voucher_no).where(sle.item_code == self.item)
		(
			frappe.qb.update(repost)
			.set(repost.modified, changed_on)
			.where((repost.item_code == self.item) | repost.voucher_no.isin(vouchers))
		).run()

	def run_audit(self):
		StockLedgerAudit(COMPANY, self.from_date).audit(self.item, WAREHOUSE, get_datetime(self.from_date))

	def get_recent_audit(self):
		return StockLedgerAudit(
			COMPANY, add_days(today(), -30), add_days(now_datetime(), -RECENT_CHANGES_DAYS)
		)

	def get_recent_start_datetime(self):
		return self.get_recent_audit().get_audit_start_datetimes().get((self.item, WAREHOUSE))

	def get_posting_datetime(self, sle):
		return frappe.db.get_value("Stock Ledger Entry", sle, "posting_datetime")

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
		self.make_repost(today(), run=False)

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
		frappe.db.set_value(
			"Company",
			COMPANY,
			{"accounts_frozen_till_date": today(), "role_allowed_for_frozen_entries": None},
		)

		with patch("frappe.log_error") as log_error:
			self.run_audit()

		self.assertFalse(self.get_scheduler_reposts())
		self.assertEqual(log_error.call_args.kwargs["reference_name"], sle)

	def test_recent_audit_skips_entries_not_changed_in_recent_days(self):
		self.make_incorrect_entry()
		self.move_entries_before_recent_days()

		self.assertIsNone(self.get_recent_start_datetime())
		self.assertIn(
			(self.item, WAREHOUSE), StockLedgerAudit(COMPANY, self.from_date).get_audit_start_datetimes()
		)

	def test_recent_audit_starts_from_earliest_new_entry(self):
		old_sle = self.make_receipt(10, 100, posting_date=add_days(today(), -10))
		frappe.db.set_value("Stock Ledger Entry", old_sle, {"stock_value": 900, "valuation_rate": 90})
		self.move_entries_before_recent_days()
		sle = self.make_receipt(5, 120, posting_date=add_days(today(), -5))
		self.make_receipt(5, 130)

		start_datetime = self.get_recent_start_datetime()
		self.get_recent_audit().audit(self.item, WAREHOUSE, start_datetime)

		self.assertEqual(start_datetime, self.get_posting_datetime(sle))
		self.assertFalse(self.get_scheduler_reposts())

	def test_cancelled_entry_starts_recent_audit_at_its_posting_time(self):
		self.make_receipt(10, 100, posting_date=add_days(today(), -10))
		sle = self.make_receipt(5, 120, posting_date=add_days(today(), -5))
		self.make_receipt(5, 130)
		self.move_entries_before_recent_days()

		voucher_no = frappe.db.get_value("Stock Ledger Entry", sle, "voucher_no")
		frappe.get_doc("Stock Entry", voucher_no).cancel()
		self.move_reposts_before_recent_days()

		self.assertEqual(self.get_recent_start_datetime(), self.get_posting_datetime(sle))

	def test_completed_repost_starts_recent_audit_at_its_posting_date(self):
		self.make_receipt(10, 100, posting_date=add_days(today(), -10))
		self.make_receipt(5, 120, posting_date=add_days(today(), -5))
		self.move_entries_before_recent_days()

		self.make_repost(add_days(today(), -10))

		self.assertEqual(self.get_recent_start_datetime(), get_datetime(add_days(today(), -10)))

	def test_failed_repost_starts_recent_audit_at_its_posting_date(self):
		self.make_receipt(10, 100, posting_date=add_days(today(), -10))
		self.move_entries_before_recent_days()

		repost = self.make_repost(add_days(today(), -10), run=False)
		frappe.db.set_value("Repost Item Valuation", repost.name, "status", "Failed")

		self.assertEqual(self.get_recent_start_datetime(), get_datetime(add_days(today(), -10)))

	def test_audit_is_queued_for_every_company(self):
		with patch("frappe.enqueue") as enqueue:
			audit_stock_ledger_entries()

		self.assertEqual(enqueue.call_count, frappe.db.count("Company"))
		self.assertIsNone(enqueue.call_args.kwargs["changed_since"])

	def test_recent_audit_is_queued_with_changes_of_last_7_days(self):
		run_at = get_datetime("2026-11-10 01:00:00")
		with (
			patch("frappe.enqueue") as enqueue,
			patch("erpnext.stock.stock_ledger_audit.now_datetime", return_value=run_at),
		):
			audit_recent_stock_ledger_entries()

		self.assertEqual(enqueue.call_count, frappe.db.count("Company"))
		self.assertEqual(enqueue.call_args.kwargs["changed_since"], get_datetime("2026-11-03 01:00:00"))

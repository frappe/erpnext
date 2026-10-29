# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime, today

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.process_period_closing_voucher import process_period_closing_voucher
from erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher import (
	ProcessPeriodClosingVoucher,
	cancel_pcv_processing,
	pause_pcv_processing,
	process_individual_date,
	resume_pcv_processing,
	schedule_next_date,
	start_pcv_processing,
	summarize_and_post_ledger_entries,
)
from erpnext.accounts.utils import get_fiscal_year

test_dependencies = ["Journal Entry"]


class TestProcessPeriodClosingVoucher(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.legacy_controller = frappe.db.get_single_value(
			"Accounts Settings", "use_legacy_controller_for_pcv"
		)
		frappe.db.set_single_value("Accounts Settings", "use_legacy_controller_for_pcv", 0)
		self.company = "_Test Company"

	def make_period_closing_voucher(self, posting_date, submit=True):
		fy = get_fiscal_year(posting_date, company="_Test Company")
		pcv = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": posting_date or today(),
				"period_start_date": fy[1],
				"period_end_date": fy[2],
				"company": self.company,
				"fiscal_year": fy[0],
				"closing_account_head": "Retained Earnings - _TC",
				"remarks": "closing",
			}
		)
		pcv.insert()
		if submit:
			pcv.submit()

		return pcv

	def make_process_pcv(self, submit=True):
		with (
			patch.object(ProcessPeriodClosingVoucher, "get_dates", return_value=[get_datetime(today())]),
			patch.object(process_period_closing_voucher, "is_scheduler_inactive", return_value=True),
		):
			self.pcv = self.make_period_closing_voucher(posting_date=today())
			ppcv = frappe.get_doc(
				"Process Period Closing Voucher", {"parent_pcv": self.pcv.name, "docstatus": 1}
			)
			if not submit:
				ppcv.cancel()
				ppcv = frappe.get_doc(doctype=ppcv.doctype, parent_pcv=self.pcv.name).insert()
		return ppcv

	def set_processing_date_status(self, row_name, status):
		frappe.db.set_value(
			"Process Period Closing Voucher Detail",
			row_name,
			"status",
			status,
		)

	def test_reject_processing_closed_period(self):
		make_journal_entry(
			posting_date=today(), amount=1000, account1="Cash - _TC", account2="Sales - _TC"
		).submit()
		frappe.db.set_single_value("Accounts Settings", "use_legacy_controller_for_pcv", 1)
		pcv = self.make_period_closing_voucher(today())
		self.assertEqual(pcv.reload().gle_processing_status, "Completed")
		gl_filters = {"voucher_type": pcv.doctype, "voucher_no": pcv.name, "is_cancelled": 0}
		balance_filters = {"period_closing_voucher": pcv.name}
		gl_count = frappe.db.count("GL Entry", gl_filters)
		balance_count = frappe.db.count("Account Closing Balance", balance_filters)
		self.assertGreater(gl_count, 0)
		self.assertGreater(balance_count, 0)

		for status in ("Completed", "In Progress"):
			with self.subTest(status=status):
				pcv.db_set("gle_processing_status", status)
				with self.assertRaises(frappe.ValidationError):
					frappe.get_doc(doctype="Process Period Closing Voucher", parent_pcv=pcv.name).insert()

		self.assertEqual(frappe.db.count("GL Entry", gl_filters), gl_count)
		self.assertEqual(frappe.db.count("Account Closing Balance", balance_filters), balance_count)

	def test_completed_processing_cannot_post_again(self):
		make_journal_entry(
			posting_date=today(), amount=1000, account1="Cash - _TC", account2="Sales - _TC"
		).submit()
		ppcv = self.make_process_pcv()
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(doctype=ppcv.doctype, parent_pcv=self.pcv.name).insert()

		pause_pcv_processing(ppcv.name)
		self.assertEqual(ppcv.reload().status, "Paused")
		with patch.object(process_period_closing_voucher, "is_scheduler_inactive", return_value=True):
			resume_pcv_processing(ppcv.name)
		self.assertEqual(ppcv.reload().status, "Running")

		with patch.object(process_period_closing_voucher, "schedule_next_date"):
			for row in ppcv.normal_balances + ppcv.z_opening_balances:
				self.set_processing_date_status(row.name, "Running")
				process_individual_date(
					ppcv.name, row.name, row.processing_date, row.report_type, row.parentfield
				)
		summarize_and_post_ledger_entries(ppcv.name)
		self.assertEqual(ppcv.reload().status, "Completed")
		self.assertEqual(self.pcv.reload().gle_processing_status, "Completed")
		gl_filters = {"voucher_type": self.pcv.doctype, "voucher_no": self.pcv.name, "is_cancelled": 0}
		balance_filters = {"period_closing_voucher": self.pcv.name}
		gl_count = frappe.db.count("GL Entry", gl_filters)
		balance_count = frappe.db.count("Account Closing Balance", balance_filters)
		self.assertEqual(gl_count, 2)
		self.assertEqual(
			frappe.db.get_value(
				"Account Closing Balance", {**balance_filters, "account": "Cash - _TC"}, "debit"
			),
			1000,
		)

		with patch.object(frappe, "enqueue") as enqueue:
			for action in (
				start_pcv_processing,
				pause_pcv_processing,
				resume_pcv_processing,
				schedule_next_date,
				summarize_and_post_ledger_entries,
			):
				with self.subTest(action=action.__name__):
					action(ppcv.name)
					self.assertEqual(ppcv.reload().status, "Completed")
				enqueue.assert_not_called()

		# A stale queued summary must also notice that its parent has already closed.
		ppcv.db_set("status", "Running")
		with self.assertRaises(frappe.ValidationError):
			summarize_and_post_ledger_entries(ppcv.name)
		self.assertEqual(frappe.db.count("GL Entry", gl_filters), gl_count)
		self.assertEqual(frappe.db.count("Account Closing Balance", balance_filters), balance_count)

	def test_reject_duplicate_from_stale_transaction(self):
		if frappe.db.db_type != "mariadb":
			self.skipTest(
				"MariaDB locking reads must see duplicates committed after the transaction snapshot"
			)

		ppcv = self.make_process_pcv()
		ppcv.cancel()
		pcv = self.pcv
		duplicate = frappe.get_doc(doctype="Process Period Closing Voucher", parent_pcv=pcv.name)
		# Allocate the name before the snapshot so naming-series locks cannot mask the duplicate check.
		duplicate.set_new_name()
		frappe.db.commit()
		primary_connection = frappe.local.db
		frappe.connect()
		secondary_connection = frappe.local.db
		try:
			# Establish the second request's snapshot before the first request creates its voucher.
			frappe.get_doc(pcv.doctype, pcv.name)
			frappe.local.db = primary_connection
			with patch.object(ProcessPeriodClosingVoucher, "get_dates", return_value=[get_datetime(today())]):
				frappe.get_doc(doctype="Process Period Closing Voucher", parent_pcv=pcv.name).insert()
			frappe.db.commit()

			frappe.local.db = secondary_connection
			# Snapshot isolation can reject the locking read instead of returning the committed duplicate.
			with self.assertRaisesRegex(
				(frappe.ValidationError, frappe.QueryDeadlockError),
				"already exists|tabProcess Period Closing Voucher",
			):
				duplicate.insert()
			frappe.db.rollback()
			with self.assertRaisesRegex(frappe.ValidationError, "already exists"):
				duplicate.insert()
		finally:
			secondary_connection.rollback()
			secondary_connection.close()
			frappe.local.db = primary_connection
			for name in frappe.get_all(
				"Process Period Closing Voucher", filters={"parent_pcv": pcv.name}, pluck="name"
			):
				frappe.delete_doc("Process Period Closing Voucher", name)
			pcv.reload().cancel()
			pcv.delete()
			frappe.db.set_single_value(
				"Accounts Settings", "use_legacy_controller_for_pcv", self.legacy_controller
			)
			frappe.db.commit()

	def test_start_waits_for_running_dates_and_summary(self):
		make_journal_entry(
			posting_date=today(), amount=1000, account1="Cash - _TC", account2="Sales - _TC"
		).submit()
		ppcv = self.make_process_pcv()
		with (
			patch.object(process_period_closing_voucher, "is_scheduler_inactive", return_value=False),
			patch.object(frappe, "enqueue") as enqueue,
		):
			start_pcv_processing(ppcv.name)
			self.assertTrue(
				all(
					row.status == "Running" for row in ppcv.reload().normal_balances + ppcv.z_opening_balances
				)
			)
			enqueue.reset_mock()
			start_pcv_processing(ppcv.name)
			self.assertEqual(ppcv.reload().status, "Running")
			enqueue.assert_not_called()

		with patch.object(process_period_closing_voucher, "schedule_next_date"):
			for row in ppcv.normal_balances + ppcv.z_opening_balances:
				process_individual_date(
					ppcv.name, row.name, row.processing_date, row.report_type, row.parentfield
				)
		self.assertTrue(
			all(row.status == "Completed" for row in ppcv.reload().normal_balances + ppcv.z_opening_balances)
		)
		with patch.object(frappe, "enqueue") as enqueue:
			start_pcv_processing(ppcv.name)
			self.assertEqual(ppcv.reload().status, "Running")
			enqueue.assert_called_once()
			self.assertEqual(
				enqueue.call_args.kwargs["method"],
				"erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.summarize_and_post_ledger_entries",
			)

		summarize_and_post_ledger_entries(ppcv.name)
		self.assertEqual(ppcv.reload().status, "Completed")
		self.assertEqual(self.pcv.reload().gle_processing_status, "Completed")
		self.assertEqual(frappe.db.count("GL Entry", {"voucher_no": self.pcv.name, "is_cancelled": 0}), 2)
		self.assertEqual(
			frappe.db.get_value(
				"Account Closing Balance",
				{"period_closing_voucher": self.pcv.name, "account": "Cash - _TC"},
				"debit",
			),
			1000,
		)

	def test_processing_requires_submitted_vouchers(self):
		pcv = self.make_period_closing_voucher(today(), submit=False)
		with self.assertRaisesRegex(frappe.ValidationError, "must be submitted before processing"):
			frappe.get_doc(doctype="Process Period Closing Voucher", parent_pcv=pcv.name).insert()
		pcv.delete()

		ppcv = self.make_process_pcv(submit=False)
		processing_actions = (
			start_pcv_processing,
			pause_pcv_processing,
			resume_pcv_processing,
			schedule_next_date,
			summarize_and_post_ledger_entries,
		)
		with patch.object(frappe, "enqueue") as enqueue:
			for action in processing_actions:
				with self.subTest(action=action.__name__, docstatus=0):
					with self.assertRaisesRegex(
						frappe.ValidationError, "must be submitted before processing"
					):
						action(ppcv.name)
			enqueue.assert_not_called()
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": self.pcv.name}))
		self.assertFalse(
			frappe.db.exists("Account Closing Balance", {"period_closing_voucher": self.pcv.name})
		)

		with (
			patch.object(ProcessPeriodClosingVoucher, "get_dates", return_value=[get_datetime(today())]),
			patch.object(process_period_closing_voucher, "is_scheduler_inactive", return_value=False),
			patch.object(frappe, "enqueue"),
		):
			ppcv.submit()
		self.assertEqual(ppcv.reload().status, "Running")
		self.assertTrue(
			all(row.status == "Running" for row in ppcv.normal_balances + ppcv.z_opening_balances)
		)

		with self.set_user("Guest"):
			for action in (
				start_pcv_processing,
				pause_pcv_processing,
				resume_pcv_processing,
				schedule_next_date,
				cancel_pcv_processing,
			):
				with self.assertRaises(frappe.PermissionError):
					action(ppcv.name)

		with self.assertRaises(frappe.ValidationError):
			cancel_pcv_processing(ppcv.name)
		ppcv.reload().cancel()
		self.assertEqual(ppcv.reload().status, "Cancelled")
		self.assertTrue(
			all(row.status == "Cancelled" for row in ppcv.normal_balances + ppcv.z_opening_balances)
		)

		with patch.object(frappe, "enqueue") as enqueue:
			for action in processing_actions:
				with self.subTest(action=action.__name__, docstatus=2):
					with self.assertRaisesRegex(
						frappe.ValidationError, "must be submitted before processing"
					):
						action(ppcv.name)
			enqueue.assert_not_called()

		with (
			patch.object(ProcessPeriodClosingVoucher, "get_dates", return_value=[get_datetime(today())]),
			patch.object(process_period_closing_voucher, "is_scheduler_inactive", return_value=True),
		):
			ppcv = frappe.get_doc(doctype=ppcv.doctype, parent_pcv=self.pcv.name).insert().submit()
		pause_pcv_processing(ppcv.name)
		self.assertEqual(ppcv.reload().status, "Paused")
		self.pcv.reload().cancel()
		self.assertEqual(ppcv.reload().docstatus, 2)
		self.assertEqual(ppcv.status, "Cancelled")
		self.assertTrue(
			all(row.status == "Cancelled" for row in ppcv.normal_balances + ppcv.z_opening_balances)
		)
		with self.assertRaises(frappe.CancelledLinkError):
			frappe.get_doc(doctype=ppcv.doctype, parent_pcv=self.pcv.name).insert()
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": self.pcv.name}))
		self.assertFalse(
			frappe.db.exists("Account Closing Balance", {"period_closing_voucher": self.pcv.name})
		)

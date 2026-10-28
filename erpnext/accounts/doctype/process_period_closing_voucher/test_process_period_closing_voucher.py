# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
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
from erpnext.tests.utils import ERPNextTestSuite


class TestProcessPeriodClosingVoucher(ERPNextTestSuite):
	def setUp(self):
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

	def get_row_name(self, ppcv_name, rpt_type, parentfield):
		return frappe.db.get_all(
			"Process Period Closing Voucher Detail",
			filters={"parent": ppcv_name, "report_type": rpt_type, "parentfield": parentfield},
			order_by="report_type, idx",
			pluck="name",
			limit=1,
		)[0]

	def get_processing_date_closing_balance(self, row_name):
		return frappe.db.get_value(
			"Process Period Closing Voucher Detail",
			row_name,
			"closing_balance",
		)

	def test_opening_balance_double_counting(self):
		opening_jv = make_journal_entry(
			posting_date=today(),
			amount=10,
			account1="Cash - _TC",
			account2="Debtors - _TC",
			company=self.company,
			save=False,
		)
		opening_jv.accounts[1].party_type = "Customer"
		opening_jv.accounts[1].party = "_Test Customer"
		opening_jv.is_opening = "Yes"
		opening_jv.save()
		opening_jv.submit()

		jv = make_journal_entry(
			posting_date=today(),
			amount=120,
			account1="Debtors - _TC",
			account2="Sales - _TC",
			company=self.company,
			save=False,
		)
		jv.accounts[0].party_type = "Customer"
		jv.accounts[0].party = "_Test Customer"
		jv.save()
		jv.submit()

		ppcv = self.make_process_pcv()
		self.assertEqual(self.pcv.is_first_period_closing_voucher(), True)

		# P&L balance
		parentfield = "normal_balances"
		rpt_type = "Profit and Loss"
		# status has to be set to 'Running' for logic to run
		row_name = self.get_row_name(ppcv.name, rpt_type, parentfield)
		self.set_processing_date_status(row_name, "Running")
		process_individual_date(ppcv.name, row_name, today(), rpt_type, parentfield)
		bal = frappe.parse_json(self.get_processing_date_closing_balance(row_name))
		self.assertEqual(len(bal), 1)
		expected_pl = {
			"account": "Sales - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"debit": 0.0,
			"credit": 120.0,
			"debit_in_account_currency": 0.0,
			"credit_in_account_currency": 120.0,
		}
		for k in expected_pl.keys():
			with self.subTest(k):
				self.assertEqual(expected_pl[k], bal[0][k])

		# Balance sheet balance
		rpt_type = "Balance Sheet"
		row_name = self.get_row_name(ppcv.name, rpt_type, parentfield)
		self.set_processing_date_status(row_name, "Running")
		process_individual_date(ppcv.name, row_name, today(), rpt_type, parentfield)
		bal = frappe.parse_json(self.get_processing_date_closing_balance(row_name))
		self.assertEqual(len(bal), 1)
		expected_bs = {
			"account": "Debtors - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"debit": 120.0,
			"credit": 0.0,
			"debit_in_account_currency": 120.0,
			"credit_in_account_currency": 0.0,
		}
		for k in expected_bs.keys():
			with self.subTest(k):
				self.assertEqual(expected_bs[k], bal[0][k])

		# Opening balance
		parentfield = "z_opening_balances"
		rpt_type = "Balance Sheet"
		row_name = self.get_row_name(ppcv.name, rpt_type, parentfield)
		self.set_processing_date_status(row_name, "Running")
		process_individual_date(ppcv.name, row_name, today(), rpt_type, parentfield)
		bal = frappe.parse_json(self.get_processing_date_closing_balance(row_name))
		self.assertEqual(len(bal), 2)
		opening_cash = next(x for x in bal if x["account"] == "Cash - _TC")
		expected_opening_cash = {
			"account": "Cash - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"debit": 10.0,
			"credit": 0.0,
			"debit_in_account_currency": 10.0,
			"credit_in_account_currency": 0.0,
			"account_currency": "INR",
		}
		for k in expected_opening_cash.keys():
			with self.subTest(k):
				self.assertEqual(expected_opening_cash[k], opening_cash[k])

		opening_debtors = next(x for x in bal if x["account"] == "Debtors - _TC")
		expected_opening_debtors = {
			"account": "Debtors - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"debit": 0.0,
			"credit": 10.0,
			"debit_in_account_currency": 0.0,
			"credit_in_account_currency": 10.0,
			"account_currency": "INR",
		}
		for k in expected_opening_debtors.keys():
			with self.subTest(k):
				self.assertEqual(expected_opening_debtors[k], opening_debtors[k])

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

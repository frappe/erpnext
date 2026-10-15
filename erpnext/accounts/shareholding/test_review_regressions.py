# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.report.equity_position.equity_position import execute as positions
from erpnext.accounts.report.share_balance.share_balance import execute as balances
from erpnext.accounts.shareholding.posting import assert_journal_unreconciled
from erpnext.accounts.shareholding.test_helpers import ShareholdingTestCase


class TestShareholdingReviewRegressions(ShareholdingTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.savepoint("shareholding_review_case")
		self.addCleanup(frappe.db.rollback, save_point="shareholding_review_case")

	def issue(self, **values):
		return self.create_transaction(
			transaction_type="Issue",
			to_shareholder=self.create_shareholder(),
			from_share_number=1,
			to_share_number=3,
			face_value_per_share=10,
			rate_per_share=15,
			**values,
		)

	def test_cancel_rejects_changed_submitted_range(self):
		issue = self.issue()
		transfer = self.create_transaction(
			transaction_type="Transfer",
			from_shareholder=issue.to_shareholder,
			to_shareholder=self.create_shareholder(),
			from_share_number=1,
			to_share_number=3,
		)
		transfer.from_share_number = 4
		transfer.to_share_number = 6
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be changed during cancellation"):
			transfer.cancel()
		self.assertFalse(
			frappe.db.exists("Share Ledger Entry", {"share_transaction": transfer.name, "is_reversal": 1})
		)

	def test_reports_reject_incomplete_legacy_history(self):
		frappe.get_doc(
			{
				"doctype": "Share Transfer",
				"name": "_Test Unmapped Legacy Issue",
				"docstatus": 1,
				"company": self.company,
				"transfer_type": "Issue",
				"date": nowdate(),
				"from_no": 1,
				"to_no": 3,
				"no_of_shares": 3,
			}
		).db_insert()
		for report, filters in (
			(positions, {"company": self.company}),
			(balances, {"company": self.company, "date": nowdate()}),
		):
			with self.assertRaisesRegex(frappe.ValidationError, "migration"):
				report(filters)

	def test_cancellation_matches_accounting_history_setting(self):
		issue_date = add_days(nowdate(), -2)
		issue = self.issue(posting_date=issue_date)
		journal = frappe.get_doc("Journal Entry", issue.journal_entry)
		journal.submit()
		with patch("erpnext.accounts.utils.is_immutable_ledger_enabled", return_value=False):
			issue.cancel()
		self.assertEqual(
			positions({"company": self.company, "share_class": self.share_class, "as_of_date": issue_date})[
				1
			],
			[],
		)
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": journal.name, "is_cancelled": 0}))

	def test_immutable_cancellation_uses_the_gl_reversal_date(self):
		issue_date = add_days(nowdate(), -2)
		cancel_date = add_days(nowdate(), -1)
		issue = self.issue(posting_date=issue_date)
		journal = frappe.get_doc("Journal Entry", issue.journal_entry)
		journal.submit()
		with patch("erpnext.accounts.utils.is_immutable_ledger_enabled", return_value=True), patch(
			"erpnext.accounts.general_ledger.is_immutable_ledger_enabled", return_value=True
		), patch.dict(frappe.form_dict, {"posting_date": cancel_date}):
			issue.cancel()
		self.assertTrue(
			frappe.db.exists("GL Entry", {"voucher_no": journal.name, "posting_date": cancel_date})
		)
		filters = {"company": self.company, "share_class": self.share_class}
		self.assertEqual(positions({**filters, "as_of_date": issue_date})[1][0].quantity, 3)
		self.assertEqual(positions({**filters, "as_of_date": cancel_date})[1], [])

	def test_partial_treasury_disposals_clear_rounded_cost(self):
		issue = self.issue()
		self.create_transaction(
			transaction_type="Buyback",
			from_shareholder=issue.to_shareholder,
			from_share_number=1,
			to_share_number=3,
			rate_per_share=12.345,
		)
		costs = []
		for number in (1, 2, 3):
			reissue = self.create_transaction(
				transaction_type="Reissue",
				to_shareholder=issue.to_shareholder,
				from_share_number=number,
				to_share_number=number,
				rate_per_share=15,
			)
			costs.append(reissue.treasury_cost)
		self.assertAlmostEqual(sum(costs), 37.04, places=2)
		entry = frappe.qb.DocType("Share Ledger Entry")
		from frappe.query_builder.functions import Sum

		cost = (
			frappe.qb.from_(entry)
			.select(Sum(entry.treasury_cost_change))
			.where(entry.share_class == self.share_class)
			.run()[0][0]
		)
		self.assertEqual(float(cost), 0)

	def test_cancelled_bank_allocation_does_not_block_cancellation(self):
		issue = self.issue()
		bank = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"name": "_Test Cancelled Equity Bank",
				"docstatus": 2,
				"date": nowdate(),
				"deposit": 45,
				"currency": "INR",
			}
		)
		bank.db_insert()
		frappe.get_doc(
			{
				"doctype": "Bank Transaction Payments",
				"name": "_Test Cancelled Equity Allocation",
				"parent": bank.name,
				"parenttype": "Bank Transaction",
				"parentfield": "payment_entries",
				"payment_document": "Journal Entry",
				"payment_entry": issue.journal_entry,
				"allocated_amount": 45,
			}
		).db_insert()
		assert_journal_unreconciled(issue)

	def test_allowed_accounts_user_can_read_shareholder(self):
		issue = self.issue()
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "equity-review@example.invalid",
				"first_name": "Review",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert(ignore_permissions=True)
		self.assertTrue(
			frappe.has_permission("Shareholder", "read", doc=issue.to_shareholder, user=user.name)
		)

	def test_legacy_shares_removed_and_new_sharing_denied(self):
		issue = self.issue()
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "equity-shared-review@example.invalid",
				"first_name": "Shared Review",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert(ignore_permissions=True)
		allowed = self.create_shareholder()
		other = self.create_company("_Test Shared Equity Issuer", "SEI")
		from erpnext.accounts.shareholding.folios import get_or_create_folio

		get_or_create_folio(other, issue.to_shareholder, nowdate())
		frappe.get_doc(
			{"doctype": "User Permission", "user": user.name, "allow": "Company", "for_value": self.company}
		).insert(ignore_permissions=True)
		for everyone in (0, 1):
			with self.assertRaises(frappe.PermissionError):
				frappe.share.add("Shareholder", allowed, user=user.name, everyone=everyone, read=1)
		for index, holder in enumerate((allowed, issue.to_shareholder)):
			frappe.get_doc(
				{
					"doctype": "DocShare",
					"name": f"_Test Stale Share {index}",
					"share_doctype": "Shareholder",
					"share_name": holder,
					"user": user.name,
					"read": 1,
				}
			).db_insert()
		with self.assertRaises(frappe.PermissionError):
			frappe.has_permission("Shareholder", "read", doc=issue.to_shareholder, user=user.name)
		from erpnext.patches.v17_0.remove_shareholder_document_shares import execute

		execute()
		execute()
		self.assertFalse(frappe.db.exists("DocShare", {"share_doctype": "Shareholder", "user": user.name}))
		self.assertFalse(
			frappe.has_permission("Shareholder", "read", doc=issue.to_shareholder, user=user.name)
		)
		self.assertTrue(frappe.has_permission("Shareholder", "read", doc=allowed, user=user.name))
		original_user = frappe.session.user
		frappe.set_user(user.name)
		try:
			self.assertFalse(frappe.get_list("Shareholder", filters={"name": issue.to_shareholder}))
			self.assertTrue(frappe.get_list("Shareholder", filters={"name": allowed}))
		finally:
			frappe.set_user(original_user)

	def test_zero_rounded_treasury_allocation_can_be_disposed(self):
		issue = self.issue()
		self.create_transaction(
			transaction_type="Buyback",
			from_shareholder=issue.to_shareholder,
			from_share_number=1,
			to_share_number=3,
			rate_per_share=0.004,
		)
		costs = []
		for number in (1, 2, 3):
			reissue = self.create_transaction(
				transaction_type="Reissue",
				to_shareholder=issue.to_shareholder,
				from_share_number=number,
				to_share_number=number,
				rate_per_share=15,
			)
			costs.append(reissue.treasury_cost)
		self.assertEqual(costs, [0, 0.01, 0])

	def test_reused_treasury_numbers_keep_new_acquisition_cost(self):
		issue = self.issue()
		self.create_transaction(
			transaction_type="Buyback",
			from_shareholder=issue.to_shareholder,
			from_share_number=1,
			to_share_number=3,
			rate_per_share=12.345,
		)
		self.create_transaction(
			transaction_type="Reissue",
			to_shareholder=issue.to_shareholder,
			from_share_number=2,
			to_share_number=3,
			rate_per_share=15,
		)
		self.create_transaction(
			transaction_type="Buyback",
			from_shareholder=issue.to_shareholder,
			from_share_number=2,
			to_share_number=2,
			rate_per_share=12,
		)
		reissue = self.create_transaction(
			transaction_type="Reissue",
			to_shareholder=issue.to_shareholder,
			from_share_number=2,
			to_share_number=2,
			rate_per_share=15,
		)
		self.assertEqual(reissue.treasury_cost, 12)

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.accounts.shareholding.test_helpers import ShareholdingTestCase


class TestShareTransactionAccounting(ShareholdingTestCase):
	def issue_ten_shares(self, **values):
		return self.create_transaction(
			transaction_type="Issue",
			to_shareholder=self.create_shareholder(),
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=10,
			rate_per_share=12,
			**values,
		)

	def set_accounting_mode(self, mode):
		settings = frappe.get_doc("Share Accounting Settings", self.company)
		settings.accounting_mode = mode
		settings.save()

	def test_direct_issue_posts_equity_gl_and_submits_settlement_payment_entry(self):
		issue = self.issue_ten_shares()

		self.assertEqual(issue.accounting_mode, "Direct")
		self.assertEqual(issue.bank_account, self.cash)
		self.assert_gl_rows(
			"Share Transaction",
			issue.name,
			{
				self.clearing_account: (120, 0),
				self.share_capital_account: (0, 100),
				self.securities_premium_account: (0, 20),
			},
		)
		payment_entry = frappe.get_doc("Payment Entry", issue.payment_entry)
		self.assertEqual(payment_entry.docstatus, 1)
		self.assertEqual(payment_entry.payment_type, "Internal Transfer")
		self.assertEqual((payment_entry.paid_from, payment_entry.paid_to), (self.clearing_account, self.cash))
		self.assert_gl_rows(
			"Payment Entry", payment_entry.name, {self.cash: (120, 0), self.clearing_account: (0, 120)}
		)

		issue.cancel()
		self.assertEqual(frappe.db.get_value("Payment Entry", payment_entry.name, "docstatus"), 2)
		self.assertFalse(
			frappe.db.exists(
				"GL Entry", {"voucher_type": "Share Transaction", "voucher_no": issue.name, "is_cancelled": 0}
			)
		)

	def test_clearing_mode_leaves_the_payment_entry_to_accounts(self):
		self.set_accounting_mode("Clearing")
		issue = self.issue_ten_shares()

		self.assertEqual(issue.accounting_mode, "Clearing")
		self.assertFalse(issue.payment_entry)
		self.assert_gl_rows(
			"Share Transaction",
			issue.name,
			{
				self.clearing_account: (120, 0),
				self.share_capital_account: (0, 100),
				self.securities_premium_account: (0, 20),
			},
		)

		payment_entry = frappe.get_doc("Payment Entry", issue.make_payment_entry())
		self.assertEqual(payment_entry.docstatus, 0)
		self.assertEqual(
			frappe.db.get_value("Share Transaction", issue.name, "payment_entry"), payment_entry.name
		)
		with self.assertRaisesRegex(frappe.ValidationError, "already exists"):
			issue.make_payment_entry()

		payment_entry.submit()
		issue.reload()
		issue.cancel()
		self.assertEqual(frappe.db.get_value("Payment Entry", payment_entry.name, "docstatus"), 2)

	def test_clearing_mode_lets_accounts_choose_the_bank_at_settlement(self):
		settings = frappe.get_doc("Share Accounting Settings", self.company)
		settings.accounting_mode = "Clearing"
		settings.default_bank_account = None
		settings.save()
		issue = self.issue_ten_shares(posting_date=add_days(nowdate(), -5))
		self.assertFalse(issue.bank_account)
		with self.assertRaisesRegex(frappe.ValidationError, "Bank or Cash Account"):
			issue.make_payment_entry()

		payment_entry = frappe.get_doc(
			"Payment Entry", issue.make_payment_entry(bank_account=self.cash, reference_no="CHQ-1")
		)
		self.assertEqual(payment_entry.paid_to, self.cash)
		self.assertEqual(payment_entry.posting_date, getdate(nowdate()))
		self.assertEqual(payment_entry.reference_no, "CHQ-1")
		issue.reload()
		self.assertEqual((issue.bank_account, issue.reference_no), (self.cash, "CHQ-1"))

	def test_accounting_preview_lists_accounts_before_and_after_submit(self):
		draft = frappe.get_doc(
			{
				"doctype": "Share Transaction",
				"company": self.company,
				"share_class": self.share_class,
				"posting_date": nowdate(),
				"transaction_type": "Issue",
				"to_shareholder": self.create_shareholder(),
				"from_share_number": 1,
				"to_share_number": 10,
				"face_value_per_share": 10,
				"rate_per_share": 12,
			}
		).insert()
		expected = {
			self.clearing_account: (120, 0),
			self.share_capital_account: (0, 100),
			self.securities_premium_account: (0, 20),
		}
		self.assertEqual(
			{row["account"]: (row["debit"], row["credit"]) for row in draft.get_accounting_preview()},
			expected,
		)
		draft.submit()
		self.assertEqual(
			{row.account: (row.debit, row.credit) for row in draft.get_accounting_preview()}, expected
		)

	def test_treasury_cost_drives_buyback_reissue_and_retirement_entries(self):
		original_holder = self.create_shareholder()
		new_holder = self.create_shareholder()
		self.create_transaction(
			transaction_type="Issue",
			to_shareholder=original_holder,
			from_share_number=1,
			to_share_number=20,
			face_value_per_share=10,
			rate_per_share=12,
		)

		buyback = self.create_transaction(
			transaction_type="Buyback",
			from_shareholder=original_holder,
			from_share_number=1,
			to_share_number=5,
			rate_per_share=14,
		)
		self.assert_gl_rows(
			"Share Transaction",
			buyback.name,
			{self.treasury_shares_account: (70, 0), self.clearing_account: (0, 70)},
		)
		buyback_payment = frappe.get_doc("Payment Entry", buyback.payment_entry)
		self.assertEqual(
			(buyback_payment.paid_from, buyback_payment.paid_to), (self.cash, self.clearing_account)
		)

		reissue = self.create_transaction(
			transaction_type="Reissue",
			to_shareholder=new_holder,
			from_share_number=1,
			to_share_number=2,
			rate_per_share=16,
		)
		self.assertEqual(reissue.treasury_cost, 28)
		self.assert_gl_rows(
			"Share Transaction",
			reissue.name,
			{
				self.clearing_account: (32, 0),
				self.treasury_shares_account: (0, 28),
				self.treasury_adjustment_account: (0, 4),
			},
		)

		retirement = self.create_transaction(
			transaction_type="Retirement",
			from_share_number=3,
			to_share_number=5,
			rate_per_share=0,
		)
		self.assertEqual(retirement.treasury_cost, 42)
		self.assertFalse(retirement.payment_entry)
		self.assert_gl_rows(
			"Share Transaction",
			retirement.name,
			{
				self.share_capital_account: (30, 0),
				self.treasury_shares_account: (0, 42),
				self.treasury_adjustment_account: (12, 0),
			},
		)

	def test_adjacent_issues_can_be_bought_back_and_retired_as_one_range(self):
		holder = self.create_shareholder()
		for first, last in ((3001, 3500), (3501, 4000)):
			self.create_transaction(
				transaction_type="Issue",
				to_shareholder=holder,
				from_share_number=first,
				to_share_number=last,
				face_value_per_share=10,
				rate_per_share=12,
			)

		buyback = self.create_transaction(
			transaction_type="Buyback",
			from_shareholder=holder,
			from_share_number=3001,
			to_share_number=4000,
			rate_per_share=12,
		)
		self.assertEqual(buyback.face_value_per_share, 10)
		retirement = self.create_transaction(
			transaction_type="Retirement",
			from_share_number=3001,
			to_share_number=4000,
		)
		self.assertEqual(retirement.face_value_per_share, 10)
		self.assertEqual(retirement.share_capital_amount, 10000)

	def test_share_class_is_reusable_and_ranges_are_company_scoped(self):
		holder = self.create_shareholder()
		first = self.create_transaction(
			transaction_type="Issue",
			to_shareholder=holder,
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=10,
			rate_per_share=12,
		)
		other_company = self.create_company("_Test Other Equity Issuer", "OEI")
		other_accounts = frappe.get_all(
			"Account",
			filters={
				"company": other_company,
				"root_type": "Liability",
				"is_group": 0,
				"account_type": ["not in", ["Payable", "Receivable"]],
			},
			pluck="name",
			limit=2,
		)
		frappe.get_doc(
			{
				"doctype": "Share Accounting Settings",
				"company": other_company,
				"accounting_mode": "Direct",
				"clearing_account": other_accounts[0],
				"share_capital_account": other_accounts[1],
				"default_bank_account": frappe.db.get_value(
					"Account", {"company": other_company, "account_type": "Cash", "is_group": 0}
				),
			}
		).insert()
		second = self.create_transaction(
			company=other_company,
			transaction_type="Issue",
			to_shareholder=holder,
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=20,
			rate_per_share=20,
		)
		self.assertEqual(first.share_class, second.share_class)
		self.assertNotEqual(first.to_folio, second.to_folio)
		self.assertEqual(second.face_value_per_share, 20)
		self.assertEqual(len(frappe.get_doc("Shareholder", holder).current_holdings), 2)

	def test_transfer_has_no_accounting_and_reverses_ownership(self):
		holder = self.create_shareholder()
		issue = self.create_transaction(
			transaction_type="Issue",
			to_shareholder=holder,
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=10,
			rate_per_share=12,
		)
		transfer = self.create_transaction(
			transaction_type="Transfer",
			from_shareholder=holder,
			to_shareholder=self.create_shareholder(),
			from_share_number=1,
			to_share_number=3,
			rate_per_share=15,
		)
		self.assertFalse(transfer.payment_entry)
		self.assertFalse(
			frappe.db.exists("GL Entry", {"voucher_type": "Share Transaction", "voucher_no": transfer.name})
		)
		self.assertEqual(frappe.db.count("Share Ledger Entry", {"share_transaction": transfer.name}), 2)
		transfer.cancel()
		self.assertEqual(
			frappe.db.count("Share Ledger Entry", {"share_transaction": transfer.name, "is_reversal": 1}), 2
		)
		payment_entry = issue.payment_entry
		issue.cancel()
		self.assertEqual(frappe.db.get_value("Payment Entry", payment_entry, "docstatus"), 2)

	def test_shareholder_child_balances_follow_ledger_and_cannot_be_manually_changed(self):
		original_holder = self.create_shareholder()
		new_holder = self.create_shareholder()
		issue = self.create_transaction(
			transaction_type="Issue",
			to_shareholder=original_holder,
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=10,
			rate_per_share=12,
		)
		balance = frappe.get_doc("Shareholder", original_holder).current_holdings
		self.assertEqual(len(balance), 1)
		self.assertEqual(balance[0].company, self.company)
		self.assertEqual(balance[0].share_class, self.share_class)
		self.assertEqual(balance[0].quantity, 10)
		self.assertEqual(balance[0].total_face_value, 100)

		shareholder = frappe.get_doc("Shareholder", original_holder)
		shareholder.current_holdings[0].quantity = 999
		shareholder.save()
		self.assertEqual(frappe.get_doc("Shareholder", original_holder).current_holdings[0].quantity, 10)

		transfer = self.create_transaction(
			transaction_type="Transfer",
			from_shareholder=original_holder,
			to_shareholder=new_holder,
			from_share_number=1,
			to_share_number=3,
			rate_per_share=15,
		)
		self.assertEqual(frappe.get_doc("Shareholder", original_holder).current_holdings[0].quantity, 7)
		self.assertEqual(frappe.get_doc("Shareholder", new_holder).current_holdings[0].quantity, 3)

		transfer.cancel()
		self.assertEqual(frappe.get_doc("Shareholder", original_holder).current_holdings[0].quantity, 10)
		self.assertFalse(frappe.get_doc("Shareholder", new_holder).current_holdings)
		issue.cancel()
		self.assertFalse(frappe.get_doc("Shareholder", original_holder).current_holdings)

	def test_folio_is_created_by_transaction_and_cannot_be_edited_directly(self):
		shareholder = self.create_shareholder()
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Share Folio",
					"company": self.company,
					"shareholder": shareholder,
				}
			).insert(ignore_permissions=True)

		issue = self.create_transaction(
			transaction_type="Issue",
			to_shareholder=shareholder,
			from_share_number=1,
			to_share_number=2,
			face_value_per_share=10,
			rate_per_share=12,
		)
		folio = frappe.get_doc("Share Folio", issue.to_folio)
		self.assertEqual(folio.shareholder, shareholder)
		self.assertEqual(folio.company, self.company)
		folio.date_of_cessation = nowdate()
		with self.assertRaises(frappe.ValidationError):
			folio.save(ignore_permissions=True)

	def test_settings_reject_an_account_used_for_two_roles(self):
		settings = frappe.get_doc("Share Accounting Settings", self.company)
		settings.securities_premium_account = self.share_capital_account
		with self.assertRaises(frappe.ValidationError):
			settings.save()

	def test_missing_settings_block_posting(self):
		settings = frappe.get_doc("Share Accounting Settings", self.company)
		settings.securities_premium_account = None
		settings.save()
		transaction = frappe.get_doc(
			{
				"doctype": "Share Transaction",
				"company": self.company,
				"share_class": self.share_class,
				"posting_date": nowdate(),
				"transaction_type": "Issue",
				"to_shareholder": self.create_shareholder(),
				"from_share_number": 1,
				"to_share_number": 10,
				"face_value_per_share": 10,
				"rate_per_share": 12,
			}
		).insert()
		with self.assertRaises(frappe.ValidationError):
			transaction.submit()
		self.assertEqual(frappe.db.get_value("Share Transaction", transaction.name, "docstatus"), 0)
		self.assertFalse(frappe.db.exists("Share Ledger Entry", {"share_transaction": transaction.name}))
		self.assertFalse(
			frappe.db.exists(
				"GL Entry", {"voucher_type": "Share Transaction", "voucher_no": transaction.name}
			)
		)
		settings.securities_premium_account = self.securities_premium_account
		settings.save()
		transaction.reload()
		transaction.submit()
		self.assert_gl_rows(
			"Share Transaction",
			transaction.name,
			{
				self.clearing_account: (120, 0),
				self.share_capital_account: (0, 100),
				self.securities_premium_account: (0, 20),
			},
		)

	def test_retirement_preview_matches_the_posted_entries(self):
		holder = self.create_shareholder()
		self.create_transaction(
			transaction_type="Issue",
			to_shareholder=holder,
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=10,
			rate_per_share=12,
		)
		self.create_transaction(
			transaction_type="Buyback",
			from_shareholder=holder,
			from_share_number=1,
			to_share_number=5,
			rate_per_share=14,
		)
		draft = frappe.get_doc(
			{
				"doctype": "Share Transaction",
				"company": self.company,
				"share_class": self.share_class,
				"posting_date": nowdate(),
				"transaction_type": "Retirement",
				"from_share_number": 1,
				"to_share_number": 5,
			}
		).insert()
		preview = {row["account"]: (row["debit"], row["credit"]) for row in draft.get_accounting_preview()}
		draft.submit()
		posted = {row.account: (row.debit, row.credit) for row in draft.get_accounting_preview()}
		self.assertEqual(preview, posted)
		self.assertEqual(preview[self.share_capital_account], (50, 0))

	def test_folio_gets_a_cessation_date_when_its_last_share_leaves(self):
		holder = self.create_shareholder()
		issue = self.issue_ten_shares()
		holder_folio = issue.to_folio
		self.assertFalse(frappe.db.get_value("Share Folio", holder_folio, "date_of_cessation"))

		transfer = self.create_transaction(
			transaction_type="Transfer",
			from_shareholder=issue.to_shareholder,
			to_shareholder=holder,
			from_share_number=1,
			to_share_number=10,
		)
		self.assertEqual(
			frappe.db.get_value("Share Folio", holder_folio, "date_of_cessation"), getdate(nowdate())
		)
		self.assertFalse(frappe.db.get_value("Share Folio", transfer.to_folio, "date_of_cessation"))

		transfer.cancel()
		self.assertFalse(frappe.db.get_value("Share Folio", holder_folio, "date_of_cessation"))

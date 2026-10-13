# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.shareholding.test_helpers import ShareholdingTestCase


class TestShareTransactionAccounting(ShareholdingTestCase):
	def test_issue_creates_draft_journal_entry_and_posts_to_general_ledger(self):
		shareholder = self.create_shareholder()
		issue = self.create_transaction(
			transaction_type="Issue",
			to_shareholder=shareholder,
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=10,
			rate_per_share=12,
		)

		journal_entry = frappe.get_doc("Journal Entry", issue.journal_entry)
		self.assertEqual(journal_entry.docstatus, 0)
		self.assertEqual(journal_entry.share_transaction, issue.name)
		self.assertEqual(issue.create_accounting_journal_entry(), journal_entry.name)
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": journal_entry.name}))
		self.assert_accounting_rows(
			journal_entry,
			{
				self.cash: (120, 0),
				self.share_capital_account: (0, 100),
				self.securities_premium_account: (0, 20),
			},
		)

		journal_entry.submit()
		general_ledger_rows = frappe.get_all(
			"GL Entry",
			filters={
				"voucher_type": "Journal Entry",
				"voucher_no": journal_entry.name,
				"is_cancelled": 0,
			},
			fields=["account", "debit", "credit"],
		)
		self.assertEqual(
			{row.account: (row.debit, row.credit) for row in general_ledger_rows},
			{
				self.cash: (120, 0),
				self.share_capital_account: (0, 100),
				self.securities_premium_account: (0, 20),
			},
		)

		issue.cancel()
		journal_entry.reload()
		self.assertEqual(journal_entry.docstatus, 2)

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
		self.assert_accounting_rows(
			frappe.get_doc("Journal Entry", buyback.journal_entry),
			{self.treasury_shares_account: (70, 0), self.cash: (0, 70)},
		)

		reissue = self.create_transaction(
			transaction_type="Reissue",
			to_shareholder=new_holder,
			from_share_number=1,
			to_share_number=2,
			rate_per_share=16,
		)
		self.assertEqual(reissue.treasury_cost, 28)
		self.assert_accounting_rows(
			frappe.get_doc("Journal Entry", reissue.journal_entry),
			{
				self.cash: (32, 0),
				self.treasury_shares_account: (0, 28),
				self.equity_adjustment_account: (0, 4),
			},
		)

		retirement = self.create_transaction(
			transaction_type="Retirement",
			from_share_number=3,
			to_share_number=5,
			rate_per_share=0,
		)
		self.assertEqual(retirement.treasury_cost, 42)
		self.assert_accounting_rows(
			frappe.get_doc("Journal Entry", retirement.journal_entry),
			{
				self.share_capital_account: (30, 0),
				self.treasury_shares_account: (0, 42),
				self.equity_adjustment_account: (12, 0),
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
		other_settings = frappe.copy_doc(frappe.get_doc("Equity Accounting Settings", self.company))
		other_settings.company = other_company
		for field in (
			"cash_or_bank_account",
			"share_capital_account",
			"securities_premium_account",
			"treasury_shares_account",
			"equity_adjustment_account",
		):
			account_name = frappe.db.get_value("Account", other_settings.get(field), "account_name")
			other_settings.set(
				field,
				frappe.db.get_value(
					"Account",
					{
						"company": other_company,
						"account_name": account_name,
						"is_group": 0,
					},
				),
			)
		other_settings.cash_or_bank_account = frappe.db.get_value(
			"Account", {"company": other_company, "account_type": "Cash", "is_group": 0}
		)
		# An issue at face value needs no premium or treasury accounts.
		other_settings.share_capital_account = frappe.db.get_value(
			"Account",
			{
				"company": other_company,
				"root_type": "Liability",
				"is_group": 0,
				"account_type": ["not in", ["Payable", "Receivable"]],
			},
		)
		other_settings.insert()
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
		self.assertFalse(transfer.journal_entry)
		self.assertFalse(frappe.db.exists("Journal Entry", {"share_transaction": transfer.name}))
		self.assertEqual(frappe.db.count("Share Ledger Entry", {"share_transaction": transfer.name}), 2)
		transfer.cancel()
		self.assertEqual(
			frappe.db.count("Share Ledger Entry", {"share_transaction": transfer.name, "is_reversal": 1}), 2
		)
		journal_name = issue.journal_entry
		issue.cancel()
		self.assertFalse(frappe.db.exists("Journal Entry", journal_name))

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

	def test_settings_validated_and_journal_source_protected(self):
		settings = frappe.get_doc("Equity Accounting Settings", self.company)
		settings.securities_premium_account = self.share_capital_account
		with self.assertRaises(frappe.ValidationError):
			settings.save()
		issue = self.create_transaction(
			transaction_type="Issue",
			to_shareholder=self.create_shareholder(),
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=10,
			rate_per_share=12,
		)
		journal = frappe.get_doc("Journal Entry", issue.journal_entry)
		duplicate = frappe.copy_doc(journal)
		duplicate.share_transaction = issue.name
		with self.assertRaises(frappe.ValidationError):
			duplicate.insert()
		journal.share_transaction = None
		with self.assertRaises(frappe.ValidationError):
			journal.save()

	def test_missing_settings_blocks_posting_and_api_cannot_override_accounts(self):
		settings = frappe.get_doc("Equity Accounting Settings", self.company)
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
		self.assertFalse(frappe.db.exists("Journal Entry", {"share_transaction": transaction.name}))
		settings.securities_premium_account = self.securities_premium_account
		settings.save()
		transaction.reload()
		transaction.share_capital_account = self.cash
		transaction.submit()
		journal = frappe.get_doc("Journal Entry", transaction.journal_entry)
		self.assert_accounting_rows(
			journal,
			{
				self.cash: (120, 0),
				self.share_capital_account: (0, 100),
				self.securities_premium_account: (0, 20),
			},
		)

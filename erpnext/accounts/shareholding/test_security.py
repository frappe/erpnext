# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.report.equity_position.equity_position import execute as positions
from erpnext.accounts.report.share_ledger.share_ledger import execute as ledger
from erpnext.accounts.shareholding.folios import get_or_create_folio
from erpnext.accounts.shareholding.test_helpers import ShareholdingTestCase


class TestShareholdingSecurity(ShareholdingTestCase):
	def issue(self, holder=None):
		return self.create_transaction(
			transaction_type="Issue",
			to_shareholder=holder or self.create_shareholder(),
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=10,
			rate_per_share=12,
		)

	def test_duplicate_issue_is_rejected(self):
		issue = self.issue()
		with self.assertRaisesRegex(frappe.ValidationError, "already been issued"):
			self.issue()
		self.assertEqual(frappe.db.count("Share Ledger Entry", {"share_class": self.share_class}), 1)
		self.assertTrue(issue.journal_entry)

	def test_retired_numbers_cannot_be_issued_again(self):
		holder = self.create_shareholder()
		self.issue(holder)
		self.create_transaction(
			transaction_type="Buyback",
			from_shareholder=holder,
			from_share_number=1,
			to_share_number=3,
			rate_per_share=14,
		)
		self.create_transaction(transaction_type="Retirement", from_share_number=1, to_share_number=3)
		with self.assertRaisesRegex(frappe.ValidationError, "already been issued"):
			self.create_transaction(
				transaction_type="Issue",
				to_shareholder=holder,
				from_share_number=1,
				to_share_number=3,
				face_value_per_share=10,
				rate_per_share=12,
			)

	def test_cancel_requires_later_transfer_to_be_reversed_first(self):
		issue = self.issue()
		self.create_transaction(
			transaction_type="Transfer",
			from_shareholder=issue.to_shareholder,
			to_shareholder=self.create_shareholder(),
			from_share_number=1,
			to_share_number=3,
		)
		with self.assertRaisesRegex(frappe.ValidationError, "Reverse later ownership"):
			issue.cancel()

	def test_ledger_cannot_be_edited_even_with_permission_bypass(self):
		issue = self.issue()
		entry = frappe.get_doc(
			"Share Ledger Entry",
			frappe.db.get_value(
				"Share Ledger Entry",
				{
					"share_transaction": issue.name,
				},
			),
		)
		entry.quantity_change = 999
		with self.assertRaisesRegex(frappe.ValidationError, "immutable"):
			entry.save(ignore_permissions=True)
		with self.assertRaisesRegex(frappe.ValidationError, "immutable"):
			frappe.delete_doc("Share Ledger Entry", entry.name, ignore_permissions=True)

	def test_balanced_journal_cannot_change_source_amounts(self):
		journal = frappe.get_doc("Journal Entry", self.issue().journal_entry)
		for row in journal.accounts:
			if row.account == self.cash:
				row.debit_in_account_currency -= 10
			elif row.account == self.share_capital_account:
				row.credit_in_account_currency -= 10
		with self.assertRaisesRegex(frappe.ValidationError, "must match the Share Transaction"):
			journal.save()

	def test_journal_cannot_be_cancelled_separately(self):
		journal = frappe.get_doc("Journal Entry", self.issue().journal_entry)
		journal.submit()
		journal.flags.from_equity_cancellation = True
		with self.assertRaisesRegex(frappe.ValidationError, "Cancel the Share Transaction"):
			journal.cancel()

	def test_company_permissions_protect_parent_and_reports(self):
		holder = self.create_shareholder()
		self.issue(holder)
		other = self.create_company("_Test Private Equity Issuer", "PEI")
		get_or_create_folio(other, holder, nowdate())
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "shareholding-limited@example.invalid",
				"first_name": "Limited",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{"doctype": "User Permission", "user": user.name, "allow": "Company", "for_value": self.company}
		).insert(ignore_permissions=True)
		original_user = frappe.session.user
		frappe.set_user(user.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Shareholder", holder).check_permission("read")
			self.assertFalse(frappe.get_list("Shareholder", filters={"name": holder}))
			with self.assertRaises(frappe.PermissionError):
				positions({"company": other})
			with self.assertRaises(frappe.PermissionError):
				ledger({"company": other})
			_data = positions({"as_of_date": nowdate()})[1]
			self.assertTrue(_data)
			self.assertTrue(all(row.company == self.company for row in _data))
		finally:
			frappe.set_user(original_user)

	def test_report_rejects_filter_operators_in_link_fields(self):
		with self.assertRaisesRegex(frappe.ValidationError, "document name"):
			positions({"company": ["!=", ""]})

	def test_positions_preserve_history_after_cancellation(self):
		holder = self.create_shareholder()
		issue_date = add_days(nowdate(), -2)
		transfer_date = add_days(nowdate(), -1)
		self.create_transaction(
			transaction_type="Issue",
			to_shareholder=holder,
			from_share_number=1,
			to_share_number=10,
			face_value_per_share=10,
			rate_per_share=12,
			posting_date=issue_date,
		)
		transfer = self.create_transaction(
			transaction_type="Transfer",
			from_shareholder=holder,
			to_shareholder=self.create_shareholder(),
			from_share_number=1,
			to_share_number=3,
			posting_date=transfer_date,
		)
		filters = {"company": self.company, "share_class": self.share_class, "shareholder": holder}
		self.assertEqual(positions({**filters, "as_of_date": issue_date})[1][0].quantity, 10)
		self.assertEqual(positions({**filters, "as_of_date": transfer_date})[1][0].quantity, 7)
		transfer.cancel()
		self.assertEqual(positions({**filters, "as_of_date": transfer_date})[1][0].quantity, 7)
		self.assertEqual(positions({**filters, "as_of_date": nowdate()})[1][0].quantity, 10)
		rows = ledger({**filters, "from_date": issue_date, "to_date": issue_date})[1]
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].quantity_change, 10)

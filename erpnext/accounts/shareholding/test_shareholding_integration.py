# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_party_details
from erpnext.accounts.doctype.shareholder.shareholder import shareholder_query
from erpnext.accounts.report.equity_position.equity_position import execute as positions
from erpnext.accounts.report.trial_balance_for_party.trial_balance_for_party import get_data
from erpnext.accounts.shareholding.folios import get_or_create_folio
from erpnext.accounts.shareholding.test_helpers import ShareholdingTestCase


class TestShareholdingIntegration(ShareholdingTestCase):
	def test_shareholder_payment_uses_legal_name(self):
		holder = self.create_shareholder()
		get_or_create_folio(self.company, holder, nowdate())
		details = get_party_details(self.company, "Shareholder", holder, nowdate())
		self.assertEqual(details["party_name"], frappe.db.get_value("Shareholder", holder, "legal_name"))
		payment = frappe.new_doc("Payment Entry")
		payment.update(
			{"company": self.company, "party_type": "Shareholder", "party": holder, "payment_type": "Pay"}
		)
		payment.party_account = details["party_account"]
		payment.set_missing_values()
		self.assertEqual(payment.party_name, details["party_name"])
		payment.validate_party_details()

	def test_shareholder_without_company_membership_cannot_be_paid(self):
		holder = self.create_shareholder()
		with self.assertRaisesRegex(frappe.ValidationError, "has no Share Folio"):
			get_party_details(self.company, "Shareholder", holder, nowdate())
		payment = frappe.new_doc("Payment Entry")
		payment.update({"company": self.company, "party_type": "Shareholder", "party": holder})
		with self.assertRaisesRegex(frappe.ValidationError, "has no Share Folio"):
			payment.validate_party_details()

	def test_payment_selector_uses_company_membership_and_permissions(self):
		allowed = self.create_shareholder()
		restricted = self.create_shareholder()
		unlinked = self.create_shareholder()
		other = self.create_company("_Test Payment Private Issuer", "PPI")
		for holder in (allowed, restricted):
			get_or_create_folio(self.company, holder, nowdate())
		get_or_create_folio(other, restricted, nowdate())
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "shareholding-selector@example.invalid",
				"first_name": "Selector",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Company",
				"for_value": self.company,
			}
		).insert(ignore_permissions=True)
		original_user = frappe.session.user
		frappe.set_user(user.name)
		try:
			rows = shareholder_query("Shareholder", "Test Holder", "name", 0, 100, {"company": self.company})
			self.assertIn(allowed, [row[0] for row in rows])
			self.assertNotIn(restricted, [row[0] for row in rows])
			self.assertNotIn(unlinked, [row[0] for row in rows])
			with self.assertRaises(frappe.PermissionError):
				shareholder_query("Shareholder", "", "name", 0, 100, {"company": other})
		finally:
			frappe.set_user(original_user)

	def test_party_trial_balance_uses_shareholder_legal_name(self):
		holder = self.create_shareholder()
		get_or_create_folio(self.company, holder, nowdate())
		rows = get_data(
			frappe._dict(
				company=self.company,
				party_type="Shareholder",
				party=holder,
				from_date=nowdate(),
				to_date=nowdate(),
				show_zero_values=1,
			),
			show_party_name=True,
		)
		self.assertEqual(rows[0]["party_name"], frappe.db.get_value("Shareholder", holder, "legal_name"))

	def test_issue_cancellation_cannot_remove_shares_before_cancelled_transfer(self):
		issue_date = add_days(nowdate(), -2)
		transfer_date = add_days(nowdate(), -1)
		issue = self.create_transaction(
			transaction_type="Issue",
			to_shareholder=self.create_shareholder(),
			posting_date=issue_date,
			from_share_number=1,
			to_share_number=3,
			face_value_per_share=10,
			rate_per_share=15,
		)
		transfer = self.create_transaction(
			transaction_type="Transfer",
			from_shareholder=issue.to_shareholder,
			to_shareholder=self.create_shareholder(),
			posting_date=transfer_date,
			from_share_number=1,
			to_share_number=3,
		)
		transfer.cancel()
		with patch("erpnext.accounts.utils.is_immutable_ledger_enabled", return_value=False):
			with self.assertRaisesRegex(frappe.ValidationError, "historical ownership"):
				issue.cancel()
		self.assertEqual(frappe.db.get_value("Share Transaction", issue.name, "docstatus"), 1)
		self.assertFalse(
			frappe.db.exists("Share Ledger Entry", {"share_transaction": issue.name, "is_reversal": 1})
		)
		rows = positions(
			{"company": self.company, "share_class": self.share_class, "as_of_date": transfer_date}
		)[1]
		self.assertEqual([(row.shareholder, row.quantity) for row in rows], [(transfer.to_shareholder, 3)])
		issue.reload()
		with patch("erpnext.accounts.utils.is_immutable_ledger_enabled", return_value=True):
			issue.cancel()
		self.assertEqual(positions({"company": self.company, "share_class": self.share_class})[1], [])
		self.assertEqual(
			positions(
				{"company": self.company, "share_class": self.share_class, "as_of_date": transfer_date}
			)[1][0].quantity,
			3,
		)

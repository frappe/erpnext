# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.report.equity_position.equity_position import execute as positions
from erpnext.accounts.report.share_balance.share_balance import execute as balances
from erpnext.accounts.report.share_ledger.share_ledger import execute as ledger
from erpnext.accounts.shareholding.entries import create_ledger_entry
from erpnext.accounts.shareholding.folios import get_or_create_folio
from erpnext.accounts.shareholding.test_helpers import ShareholdingTestCase


class TestShareholdingAccessAndIdentity(ShareholdingTestCase):
	def issue(self):
		return self.create_transaction(
			transaction_type="Issue",
			to_shareholder=self.create_shareholder(),
			from_share_number=1,
			to_share_number=3,
			face_value_per_share=10,
			rate_per_share=15,
		)

	def create_user(self, role):
		return (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"shareholding-{frappe.scrub(role)}@example.invalid",
					"first_name": "Review",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_scoped_company_permissions_filter_all_ownership_reports(self):
		self.issue()
		other = self.create_company("_Test Scoped Equity Company", "SEC")
		folio = get_or_create_folio(other, self.create_shareholder(), nowdate())
		source = frappe.get_doc(
			{
				"doctype": "Share Transaction",
				"company": other,
				"share_class": self.share_class,
				"transaction_type": "Issue",
				"posting_date": nowdate(),
				"currency": "INR",
				"from_share_number": 1,
				"to_share_number": 3,
				"number_of_shares": 3,
				"face_value_per_share": 10,
				"rate_per_share": 15,
				"docstatus": 1,
			}
		)
		source.set_new_name()
		source.db_insert()
		create_ledger_entry(source, folio, 3, nowdate())
		user = self.create_user("Accounts User")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": self.company,
				"apply_to_all_doctypes": 0,
				"applicable_for": "Share Ledger Entry",
			}
		).insert(ignore_permissions=True)
		original_user = frappe.session.user
		frappe.set_user(user)
		try:
			for report in (positions, balances, ledger):
				with self.subTest(report=report.__module__):
					rows = report({"share_class": self.share_class, "date": nowdate()})[1]
					self.assertTrue(rows)
					self.assertEqual({row.company for row in rows}, {self.company})
					with self.assertRaises(frappe.PermissionError):
						report({"company": other, "share_class": self.share_class, "date": nowdate()})
		finally:
			frappe.set_user(original_user)

	def test_api_insert_requires_each_tax_identity_field(self):
		for kind in ("Individual", "Organization", "Trust"):
			for field in ("tax_id_type", "tax_id", "tax_id_country"):
				with self.subTest(kind=kind, field=field):
					doc = frappe.copy_doc(frappe.get_doc("Shareholder", self.create_shareholder()))
					doc.shareholder_type = kind
					doc.set(field, None)
					with self.assertRaises(frappe.MandatoryError):
						doc.insert()

	def test_api_update_rejects_blank_tax_identity(self):
		doc = frappe.get_doc("Shareholder", self.create_shareholder())
		doc.tax_id = "   "
		with self.assertRaises(frappe.MandatoryError):
			doc.save()

	def test_managers_can_amend_cancelled_transactions(self):
		issue = self.issue()
		issue.cancel()
		original_user = frappe.session.user
		try:
			for role in ("Accounts Manager", "System Manager"):
				frappe.set_user("Administrator")
				user = self.create_user(role)
				frappe.set_user(user)
				self.assertTrue(frappe.has_permission("Share Transaction", "amend", doc=issue))
				amendment = frappe.copy_doc(issue)
				amendment.docstatus = 0
				amendment.amended_from = issue.name
				amendment.insert()
				self.assertEqual(amendment.docstatus, 0)
				self.assertEqual(amendment.amended_from, issue.name)
				amendment.delete()
		finally:
			frappe.set_user(original_user)

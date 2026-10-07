# Copyright (c) 2026, Aagnya Mistry and contributors
# See license.txt

"""Treasury used by the people who do the work: an accountant (Accounts User) records, a manager
(Accounts Manager) approves and sets things up. Everything here runs as them, not as Administrator."""

import frappe
from frappe.desk.search import search_link

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	TEST_COMPANY,
	create_financial_institution,
	create_investment_type,
	make_investment,
)
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	INVESTMENT_ACCOUNTS,
	make_submitted_investment,
	make_transaction,
)

ACCOUNTS_USER = "treasury.accountant@example.com"
ACCOUNTS_MANAGER = "treasury.manager@example.com"


class TestTreasuryPermissions(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_financial_institution("_Test Bank")
		create_user(ACCOUNTS_USER, "Accounts User")
		create_user(ACCOUNTS_MANAGER, "Accounts Manager")

	def test_accounts_user_can_pick_issuer_and_investment_type(self):
		with self.set_user(ACCOUNTS_USER):
			issuers = search_link("Financial Institution", "_Test Bank")
			investment_types = search_link("Investment Type", "_Test Bank FD")

		self.assertIn("_Test Bank", [row["value"] for row in issuers])
		self.assertIn("_Test Bank FD", [row["value"] for row in investment_types])

	def test_accounts_user_cannot_add_issuer(self):
		with self.set_user(ACCOUNTS_USER):
			issuer = frappe.get_doc(
				{
					"doctype": "Financial Institution",
					"institution_name": "_Test New Bank",
					"institution_type": "Bank",
				}
			)
			self.assertRaises(frappe.PermissionError, issuer.insert)

	def test_accounts_user_can_draft_but_not_approve_investment(self):
		with self.set_user(ACCOUNTS_USER):
			investment = make_investment(**INVESTMENT_ACCOUNTS).insert()
			self.assertRaises(frappe.PermissionError, investment.submit)

		self.assertEqual(frappe.db.get_value("Investment", investment.name, "docstatus"), 0)

	def test_accounts_user_can_record_purchase(self):
		investment = make_submitted_investment()

		with self.set_user(ACCOUNTS_USER):
			make_transaction(investment.name, "Purchase", gross_amount=100000).submit()

		self.assertEqual(frappe.db.get_value("Investment", investment.name, "total_cost"), 100000)

	def test_accounts_user_cannot_change_investment_settings(self):
		with self.set_user(ACCOUNTS_USER):
			settings = frappe.get_single("Investment Settings")
			settings.company = TEST_COMPANY
			self.assertRaises(frappe.PermissionError, settings.save)

	def test_accounts_manager_can_add_issuer_and_investment_type(self):
		with self.set_user(ACCOUNTS_MANAGER):
			create_financial_institution("_Test New Bank")
			create_investment_type("_Test New FD", "Deposit")

		self.assertTrue(frappe.db.exists("Financial Institution", "_Test New Bank"))
		self.assertTrue(frappe.db.exists("Investment Type", "_Test New FD"))

	def test_accounts_manager_can_link_primary_contact_to_issuer(self):
		contact = frappe.get_doc({"doctype": "Contact", "first_name": "_Test Shah"}).insert()

		with self.set_user(ACCOUNTS_MANAGER):
			frappe.get_doc(
				{
					"doctype": "Financial Institution",
					"institution_name": "_Test New Bank",
					"institution_type": "Bank",
					"primary_contact": contact.name,
				}
			).insert()

		contact.reload()
		self.assertTrue(contact.has_link("Financial Institution", "_Test New Bank"))

	def test_accounts_manager_can_approve_investment(self):
		with self.set_user(ACCOUNTS_MANAGER):
			investment = make_investment(**INVESTMENT_ACCOUNTS).insert()
			investment.submit()

		self.assertEqual(investment.status, "Active")
		self.assertEqual(investment.approved_by, ACCOUNTS_MANAGER)

	def test_accounts_manager_can_change_investment_settings(self):
		with self.set_user(ACCOUNTS_MANAGER):
			settings = frappe.get_single("Investment Settings")
			settings.company = TEST_COMPANY
			settings.save()

		self.assertEqual(frappe.db.get_single_value("Investment Settings", "company"), TEST_COMPANY)


def create_user(email, role):
	if frappe.db.exists("User", email):
		return

	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": role,
			"send_welcome_email": 0,
			"roles": [{"role": role}],
		}
	).insert()

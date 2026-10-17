# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestPartyType(ERPNextTestSuite):
	def test_managers_can_create_and_edit_party_types(self):
		for role in ("System Manager", "Accounts Manager"):
			with self.subTest(role=role):
				user = frappe.get_doc(
					doctype="User",
					email=f"party-type-{frappe.generate_hash(length=10)}@example.com",
					first_name=role,
					send_welcome_email=0,
					roles=[{"role": role}],
				).insert()
				with self.set_user(user.name):
					party_type = frappe.get_doc(
						doctype="Party Type", party_type="Sales Partner", account_type="Receivable"
					).insert()
					party_type.account_type = "Payable"
					party_type.save()
					self.assertEqual(
						frappe.get_value("Party Type", party_type.name, "account_type"), "Payable"
					)
				frappe.delete_doc("Party Type", party_type.name)

	def test_accounts_user_cannot_create_or_edit_party_types(self):
		user = frappe.get_doc(
			doctype="User",
			email=f"party-type-{frappe.generate_hash(length=10)}@example.com",
			first_name="Party Type Reader",
			send_welcome_email=0,
			roles=[{"role": "Accounts User"}],
		).insert()
		with self.set_user(user.name):
			self.assertTrue(frappe.has_permission("Party Type", "read"))
			self.assertFalse(frappe.has_permission("Party Type", "create"))
			self.assertFalse(frappe.has_permission("Party Type", "write"))

	def test_account_type_cannot_change_after_ledger_entries(self):
		party_type = frappe.get_doc(
			doctype="Party Type", party_type="Sales Partner", account_type="Receivable"
		).insert()
		journal = make_journal_entry("Debtors - _TC", "_Test Cash - _TC", 10, save=False)
		journal.accounts[0].update({"party_type": "Sales Partner", "party": "_Test Sales Partner India - 1"})
		journal.insert().submit()
		self.assertTrue(frappe.db.exists("GL Entry", {"party_type": party_type.name}))
		party_type.save()
		party_type.account_type = "Payable"
		self.assertRaises(frappe.ValidationError, party_type.save)
		journal.cancel()
		self.assertRaises(frappe.ValidationError, party_type.save)

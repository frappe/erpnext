# Copyright (c) 2026, Aagnya Mistry and contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	TEST_COMPANY,
	create_financial_institution,
	create_investment_type,
	make_investment,
)
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	make_submitted_investment,
)

CHARGES_ACCOUNT = "Bank Charges - _TC"


class TestInvestmentSettings(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_financial_institution("_Test Bank")

	def test_account_must_belong_to_company(self):
		settings = frappe.get_single("Investment Settings")
		settings.company = TEST_COMPANY
		settings.charges_account = frappe.db.get_value(
			"Account", {"company": ("!=", TEST_COMPANY), "is_group": 0}, "name"
		)

		self.assertRaises(frappe.ValidationError, settings.save)

	def test_empty_account_falls_back_to_settings(self):
		set_default_charges_account()

		investment = make_investment().insert()

		self.assertEqual(investment.charges_account, CHARGES_ACCOUNT)

	def test_own_account_is_kept(self):
		set_default_charges_account()
		own_account = frappe.db.get_value(
			"Account", {"company": TEST_COMPANY, "is_group": 0, "name": ("!=", CHARGES_ACCOUNT)}, "name"
		)

		investment = make_investment(charges_account=own_account).insert()

		self.assertEqual(investment.charges_account, own_account)

	def test_defaults_of_another_company_are_not_used(self):
		other_company = frappe.db.get_value("Company", {"name": ("!=", TEST_COMPANY)}, "name")
		settings = frappe.get_single("Investment Settings")
		settings.company = other_company
		settings.save()

		investment = make_investment().insert()

		self.assertFalse(investment.charges_account)

	def test_investment_account_is_required_here_or_in_settings(self):
		settings = frappe.get_single("Investment Settings")
		settings.company = TEST_COMPANY
		settings.investment_account = None
		settings.save()

		investment = make_investment(investment_account=None)

		self.assertRaises(frappe.ValidationError, investment.insert)

	def test_submitted_investment_takes_default_when_posting(self):
		investment = make_submitted_investment(charges_account=None)
		frappe.db.set_value("Investment", investment.name, "charges_account", None)
		set_default_charges_account()

		investment.reload()

		self.assertEqual(investment.get_account("charges_account"), CHARGES_ACCOUNT)
		self.assertEqual(
			frappe.db.get_value("Investment", investment.name, "charges_account"), CHARGES_ACCOUNT
		)


def set_default_charges_account():
	settings = frappe.get_single("Investment Settings")
	settings.company = TEST_COMPANY
	settings.charges_account = CHARGES_ACCOUNT
	settings.save()

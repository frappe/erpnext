# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	TEST_COMPANY,
	create_financial_institution,
	create_investment_type,
	make_investment,
)
from erpnext.treasury.doctype.investment_settings.investment_settings import get_default_account
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	make_submitted_investment,
)

CHARGES_ACCOUNT = "Bank Charges - _TC"


class TestInvestmentSettings(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_financial_institution("_Test Bank")

	def test_account_must_belong_to_company(self):
		other_account = frappe.db.get_value(
			"Account", {"company": ("!=", TEST_COMPANY), "is_group": 0}, "name"
		)
		settings = get_settings_with_defaults(charges_account=other_account)

		self.assertRaises(frappe.ValidationError, settings.save)

	def test_company_can_be_added_only_once(self):
		settings = get_settings_with_defaults()
		settings.append("company_accounts", {"company": TEST_COMPANY})

		self.assertRaises(frappe.ValidationError, settings.save)

	def test_each_company_uses_its_own_defaults(self):
		other_company = frappe.db.get_value("Company", {"name": ("!=", TEST_COMPANY)}, "name")
		other_charges_account = frappe.db.get_value(
			"Account", {"company": other_company, "is_group": 0, "account_type": ("!=", "Stock")}, "name"
		)
		settings = get_settings_with_defaults(charges_account=CHARGES_ACCOUNT)
		settings.append(
			"company_accounts", {"company": other_company, "charges_account": other_charges_account}
		)
		settings.save()

		self.assertEqual(get_default_account(TEST_COMPANY, "charges_account"), CHARGES_ACCOUNT)
		self.assertEqual(get_default_account(other_company, "charges_account"), other_charges_account)

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
		settings.set("company_accounts", [{"company": other_company}])
		settings.save()

		investment = make_investment().insert()

		self.assertFalse(investment.charges_account)

	def test_investment_account_is_required_here_or_in_settings(self):
		get_settings_with_defaults(investment_account=None).save()

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
	get_settings_with_defaults(charges_account=CHARGES_ACCOUNT).save()


def get_settings_with_defaults(**accounts):
	"""Investment Settings with only the test company's default accounts, not saved yet."""
	settings = frappe.get_single("Investment Settings")
	settings.set("company_accounts", [{"company": TEST_COMPANY, **accounts}])
	return settings

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

	def test_invalid_settings_are_rejected(self):
		other_account = frappe.db.get_value(
			"Account", {"company": ("!=", TEST_COMPANY), "is_group": 0}, "name"
		)
		self.assertRaises(
			frappe.ValidationError, get_settings_with_defaults(charges_account=other_account).save
		)

		settings = get_settings_with_defaults()
		settings.append("company_accounts", {"company": TEST_COMPANY})  # same company twice
		self.assertRaises(frappe.ValidationError, settings.save)

	def test_investment_takes_its_own_companys_defaults(self):
		other_company = frappe.db.get_value("Company", {"name": ("!=", TEST_COMPANY)}, "name")
		settings = frappe.get_single("Investment Settings")
		settings.set("company_accounts", [{"company": other_company}])
		settings.save()
		# another company's defaults are not used
		self.assertFalse(make_investment().insert().charges_account)

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

		# an empty account falls back to settings, an own account is kept
		self.assertEqual(make_investment().insert().charges_account, CHARGES_ACCOUNT)
		own_account = frappe.db.get_value(
			"Account", {"company": TEST_COMPANY, "is_group": 0, "name": ("!=", CHARGES_ACCOUNT)}, "name"
		)
		self.assertEqual(make_investment(charges_account=own_account).insert().charges_account, own_account)

		# the investment account is required here or in settings
		self.assertRaises(frappe.ValidationError, make_investment(investment_account=None).insert)

	def test_empty_account_after_approval_is_set_once_never_filled_while_posting(self):
		investment = make_submitted_investment(charges_account=None)
		frappe.db.set_value("Investment", investment.name, "charges_account", None)
		set_default_charges_account()
		investment.reload()

		# posting does not quietly save the default
		self.assertRaises(frappe.ValidationError, investment.get_account, "charges_account")
		self.assertFalse(frappe.db.get_value("Investment", investment.name, "charges_account"))

		investment.charges_account = CHARGES_ACCOUNT
		investment.save()
		self.assertEqual(investment.get_account("charges_account"), CHARGES_ACCOUNT)

		investment.charges_account = frappe.db.get_value(
			"Account", {"company": TEST_COMPANY, "is_group": 0, "name": ("!=", CHARGES_ACCOUNT)}, "name"
		)
		self.assertRaises(frappe.ValidationError, investment.save)


def set_default_charges_account():
	get_settings_with_defaults(charges_account=CHARGES_ACCOUNT).save()


def get_settings_with_defaults(**accounts):
	"""Investment Settings with only the test company's default accounts, not saved yet."""
	settings = frappe.get_single("Investment Settings")
	settings.set("company_accounts", [{"company": TEST_COMPANY, **accounts}])
	return settings

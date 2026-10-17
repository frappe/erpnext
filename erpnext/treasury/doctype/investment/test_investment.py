# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.tests.utils import ERPNextTestSuite

TEST_COMPANY = "_Test Company"


class TestInvestment(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_financial_institution("_Test Bank")

	def test_invalid_investment_is_rejected(self):
		create_investment_type("_Test Inactive Type", "Deposit", is_active=0)
		other_account = frappe.db.get_value(
			"Account", {"company": ("!=", TEST_COMPANY), "is_group": 0}, "name"
		)

		for invalid in (
			{"maturity_date": None},  # a deposit needs a maturity date
			{"maturity_date": nowdate()},  # maturity must come after purchase
			{"approved_amount": 0},
			{"investment_account": other_account},  # account of another company
			{"investment_type": "_Test Inactive Type"},
		):
			with self.subTest(invalid):
				self.assertRaises(frappe.ValidationError, make_investment(**invalid).insert)


def make_investment(**args):
	investment = frappe.get_doc(
		{
			"doctype": "Investment",
			"investment_type": "_Test Bank FD",
			"company": TEST_COMPANY,
			"issuer": "_Test Bank",
			"purchase_date": nowdate(),
			"maturity_date": add_days(nowdate(), 365),
			"rate_of_interest": 7.5,
			"interest_payout_type": "Cumulative",
			"compounding_frequency": "Quarterly",
			"principal_amount": 100000,
			"measurement_category": "Amortized Cost",
			"investment_account": get_company_account(),
			"approved_amount": 100000,
			"investment_rationale": "Park surplus cash",
		}
	)
	investment.update(args)
	return investment


def get_company_account():
	return frappe.db.get_value("Account", {"company": TEST_COMPANY, "is_group": 0}, "name")


def create_investment_type(name, instrument_class, is_active=1):
	if frappe.db.exists("Investment Type", name):
		return

	frappe.get_doc(
		{
			"doctype": "Investment Type",
			"investment_type": name,
			"instrument_class": instrument_class,
			"is_active": is_active,
		}
	).insert()


def create_financial_institution(name):
	if frappe.db.exists("Financial Institution", name):
		return

	frappe.get_doc(
		{"doctype": "Financial Institution", "institution_name": name, "institution_type": "Bank"}
	).insert()

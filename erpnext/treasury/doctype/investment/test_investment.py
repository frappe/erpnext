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

	def test_maturity_date_must_be_after_purchase_date(self):
		investment = make_investment(maturity_date=nowdate())
		self.assertRaises(frappe.ValidationError, investment.insert)

	def test_approved_amount_must_be_positive(self):
		investment = make_investment(approved_amount=0)
		self.assertRaises(frappe.ValidationError, investment.insert)

	def test_account_must_belong_to_company(self):
		other_account = frappe.db.get_value(
			"Account", {"company": ("!=", TEST_COMPANY), "is_group": 0}, "name"
		)
		investment = make_investment(investment_account=other_account)
		self.assertRaises(frappe.ValidationError, investment.insert)

	def test_inactive_investment_type_is_rejected(self):
		create_investment_type("_Test Inactive Type", "Deposit", is_active=0)
		investment = make_investment(investment_type="_Test Inactive Type")
		self.assertRaises(frappe.ValidationError, investment.insert)

	def test_status_follows_submit_and_cancel(self):
		investment = make_investment().insert()
		self.assertEqual(investment.status, "Draft")

		investment.submit()
		self.assertEqual(investment.status, "Active")
		self.assertEqual(investment.approved_by, frappe.session.user)

		investment.cancel()
		self.assertEqual(investment.status, "Cancelled")


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

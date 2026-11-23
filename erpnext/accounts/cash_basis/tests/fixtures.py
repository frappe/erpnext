# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Shared test data for the cash basis tests. Real database, no mocks."""

from unittest.mock import patch

import frappe

import erpnext.accounts.cash_basis as cash_basis

# The tests set the rollout scope themselves, so they do not depend on the value of
# CASH_METHOD_COUNTRIES.
TEST_COUNTRIES = ("United States",)

US_COMPANY = "_Test Cash Basis US"
US_ABBR = "_TCBU"
CUSTOMER = "_Test Cash Basis Customer"
CUSTOMER_2 = "_Test Cash Basis Customer 2"
SUPPLIER = "_Test Cash Basis Supplier"
SERVICE_ITEMS = ("_Test Cash Basis Service", "_Test Cash Basis Service 2", "_Test Cash Basis Service 3")
SERVICE_ITEM = SERVICE_ITEMS[0]
STOCK_ITEM = "_Test Cash Basis Stock Item"
EUR_CUSTOMER = "_Test Cash Basis EUR Customer"
# The calculation tests use their own unapplied accounts, so they need no Company setting.
TEST_UNAPPLIED_RECEIPTS = f"Test Unapplied Receipts - {US_ABBR}"
TEST_UNAPPLIED_PAYMENTS = f"Test Unapplied Payments - {US_ABBR}"


def get_or_create_company(
	company_name, abbr, country="United States", currency="USD", parent=None, is_group=0
):
	"""Make a company once, and commit it, so that each test does not build a chart of accounts."""
	if frappe.db.exists("Company", company_name):
		return frappe.get_doc("Company", company_name)

	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": company_name,
			"abbr": abbr,
			"country": country,
			"default_currency": currency,
			"create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "Standard",
			"parent_company": parent,
			"is_group": is_group,
		}
	).insert()
	# The setup of a chart of accounts is slow. Keep the company for all test runs.
	frappe.db.commit()  # nosemgrep -- the company is shared test data, see the comment above
	return company


def set_company_method(company_name, method, treatment="Income and Expense"):
	company = frappe.get_doc("Company", company_name)
	company.accounting_method = method
	company.unapplied_cash_treatment = treatment
	company.save()
	return company


def setup_cash_basis_master_data():
	"""Company, bank account, parties, and items for the calculation tests. Committed once."""
	get_or_create_company(US_COMPANY, US_ABBR)
	changed = False
	changed |= ensure_record(
		"Account",
		{"account_name": "Test Bank", "company": US_COMPANY},
		{"parent_account": f"Bank Accounts - {US_ABBR}", "account_type": "Bank"},
	)
	changed |= ensure_record(
		"Account",
		{"account_name": "Customer Advances Received", "company": US_COMPANY},
		{"parent_account": f"Current Liabilities - {US_ABBR}", "account_type": "Receivable"},
	)
	changed |= ensure_record(
		"Account",
		{"account_name": "Supplier Advances Paid", "company": US_COMPANY},
		{"parent_account": f"Current Assets - {US_ABBR}", "account_type": "Payable"},
	)
	changed |= ensure_record(
		"Account",
		{"account_name": "Deferred Revenue", "company": US_COMPANY},
		{"parent_account": f"Current Liabilities - {US_ABBR}"},
	)
	changed |= ensure_record(
		"Account",
		{"account_name": "Prepaid Expenses", "company": US_COMPANY},
		{"parent_account": f"Current Assets - {US_ABBR}"},
	)
	changed |= ensure_record(
		"Cost Center",
		{"cost_center_name": "Second", "company": US_COMPANY},
		{"parent_cost_center": f"{US_COMPANY} - {US_ABBR}"},
	)
	changed |= ensure_record(
		"Account",
		{"account_name": "Test Unapplied Receipts", "company": US_COMPANY},
		{"parent_account": f"Income - {US_ABBR}"},
	)
	changed |= ensure_record(
		"Account",
		{"account_name": "Test Unapplied Payments", "company": US_COMPANY},
		{"parent_account": f"Expenses - {US_ABBR}"},
	)
	changed |= ensure_record(
		"Account",
		{"account_name": "Debtors EUR", "company": US_COMPANY},
		{
			"parent_account": f"Accounts Receivable - {US_ABBR}",
			"account_type": "Receivable",
			"account_currency": "EUR",
		},
	)
	changed |= ensure_record(
		"Account",
		{"account_name": "Unrealized Exchange Gain/Loss", "company": US_COMPANY},
		{"parent_account": f"Indirect Income - {US_ABBR}"},
	)
	changed |= ensure_record(
		"Customer",
		{"customer_name": EUR_CUSTOMER},
		{
			"customer_type": "Company",
			"default_currency": "EUR",
			"accounts": [{"company": US_COMPANY, "account": f"Debtors EUR - {US_ABBR}"}],
		},
		key="name",
	)
	for customer in (CUSTOMER, CUSTOMER_2):
		changed |= ensure_record(
			"Customer", {"customer_name": customer}, {"customer_type": "Company"}, key="name"
		)
	changed |= ensure_record(
		"Supplier", {"supplier_name": SUPPLIER}, {"supplier_type": "Company"}, key="name"
	)
	for item_code in SERVICE_ITEMS:
		changed |= ensure_record(
			"Item",
			{"item_code": item_code},
			{"item_group": "All Item Groups", "stock_uom": "Nos", "is_stock_item": 0},
			key="name",
		)
	changed |= ensure_record(
		"Item",
		{"item_code": STOCK_ITEM},
		{"item_group": "All Item Groups", "stock_uom": "Nos", "is_stock_item": 1, "valuation_rate": 40},
		key="name",
	)
	if changed:
		frappe.db.commit()  # nosemgrep -- shared master data for the cash basis tests


def ensure_record(doctype, filters, values, key=None):
	lookup = {"name": filters[next(iter(filters))]} if key == "name" else filters
	if frappe.db.exists(doctype, lookup):
		return False
	frappe.get_doc({"doctype": doctype, **filters, **values}).insert()
	return True


def acc(name: str) -> str:
	return f"{name} - {US_ABBR}"


def put_test_countries_in_scope(test_class):
	"""Set the rollout constant for the tests of the class, whatever its value in the code."""
	scope = patch.object(cash_basis, "CASH_METHOD_COUNTRIES", TEST_COUNTRIES)
	scope.start()
	test_class.addClassCleanup(scope.stop)

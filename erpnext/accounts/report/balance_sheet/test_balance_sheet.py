# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today

from erpnext.accounts.report.balance_sheet.balance_sheet import execute

COMPANY = "_Test Company 6"
COMPANY_SHORT_NAME = "_TC6"


class TestBalanceSheet(FrappeTestCase):
	def test_balance_sheet(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_sales_invoice,
		)

		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company 6'")
		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company 6'")
		frappe.db.sql("delete from `tabGL Entry` where company='_Test Company 6'")

		make_purchase_invoice(
			company="_Test Company 6",
			warehouse="Finished Goods - _TC6",
			expense_account="Cost of Goods Sold - _TC6",
			cost_center="Main - _TC6",
			qty=10,
			rate=100,
		)
		create_sales_invoice(
			company="_Test Company 6",
			debit_to="Debtors - _TC6",
			income_account="Sales - _TC6",
			cost_center="Main - _TC6",
			qty=5,
			rate=110,
		)
		filters = frappe._dict(
			company="_Test Company 6",
			period_start_date=today(),
			period_end_date=today(),
			periodicity="Yearly",
		)
		result = execute(filters)[1]
		for account_dict in result:
			if account_dict.get("account") == "Current Liabilities - _TC6":
				self.assertEqual(account_dict.total, 1000)
			if account_dict.get("account") == "Current Assets - _TC6":
				self.assertEqual(account_dict.total, 550)

	def test_unclosed_profit_of_earlier_years_is_not_provisional(self):
		create_account("My Bank", f"Bank Accounts - {COMPANY_SHORT_NAME}", COMPANY)
		filters = frappe._dict(
			company=COMPANY,
			filter_based_on="Date Range",
			period_start_date="2026-01-01",
			period_end_date="2026-12-31",
			periodicity="Yearly",
			accumulated_values=1,
		)
		unclosed, provisional = get_profit_loss_rows(filters)

		for amount, posting_date in ((1000, "2025-06-01"), (300, "2026-06-01")):
			make_journal_entry(
				[
					dict(account_name="My Bank", debit_in_account_currency=amount),
					dict(account_name="Sales", credit_in_account_currency=amount),
				],
				posting_date=posting_date,
			)

		self.assertEqual(get_profit_loss_rows(filters), (unclosed + 1000, provisional + 300))

		# a current loss that exactly offsets all earlier profit must still be shown
		make_journal_entry(
			[
				dict(account_name="Capital Stock", credit_in_account_currency=1300),
				dict(account_name="Sales", debit_in_account_currency=1300),
			],
			posting_date="2026-07-01",
		)
		self.assertEqual(get_profit_loss_rows(filters), (unclosed + 1000, provisional - 1000))

	def test_presentation_currency_does_not_depend_on_unrelated_accounts(self):
		create_account("USD Loan", f"Loans (Liabilities) - {COMPANY_SHORT_NAME}", COMPANY, "USD")
		frappe.get_doc(
			doctype="Currency Exchange",
			date="2026-12-31",
			from_currency="USD",
			to_currency="INR",
			exchange_rate=85,
		).insert(ignore_if_duplicate=True)
		filters = frappe._dict(
			company=COMPANY,
			filter_based_on="Date Range",
			period_start_date="2026-01-01",
			period_end_date="2026-12-31",
			periodicity="Yearly",
			accumulated_values=1,
			presentation_currency="USD",
		)
		_, provisional = get_loan_and_provisional_profit(filters)

		jv = frappe.new_doc("Journal Entry", company=COMPANY, posting_date="2026-05-01", multi_currency=1)
		jv.append("accounts", {"account": f"Cash - {COMPANY_SHORT_NAME}", "debit_in_account_currency": 8000})
		jv.append(
			"accounts",
			{
				"account": f"USD Loan - {COMPANY_SHORT_NAME}",
				"credit_in_account_currency": 100,
				"exchange_rate": 80,
			},
		)
		jv.submit()
		# 8000 INR at the closing rate of 85, not the loan's own 100 USD
		self.assertEqual(get_loan_and_provisional_profit(filters), (94.12, provisional))

		make_journal_entry(
			[
				dict(account_name="Administrative Expenses", debit_in_account_currency=850),
				dict(account_name="Accrued Expenses", credit_in_account_currency=850),
			],
			posting_date="2026-06-01",
		)
		self.assertEqual(get_loan_and_provisional_profit(filters), (94.12, flt(provisional - 10, 2)))


def get_profit_loss_rows(filters):
	rows = {row.get("account"): flt(row.get("total")) for row in execute(frappe._dict(filters))[1]}
	return (
		rows.get("'Unclosed Fiscal Years Profit / Loss (Credit)'", 0),
		rows.get("'Provisional Profit / Loss (Credit)'", 0),
	)


def make_journal_entry(rows, posting_date=None):
	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = posting_date or today()
	jv.company = COMPANY
	jv.user_remark = "test"

	for row in rows:
		row["account"] = row.pop("account_name") + " - " + COMPANY_SHORT_NAME
		jv.append("accounts", row)

	jv.insert()
	jv.submit()


def get_loan_and_provisional_profit(filters):
	rows = {row.get("account"): flt(row.get("total"), 2) for row in execute(frappe._dict(filters))[1]}
	provisional = rows.get("'Provisional Profit / Loss (Credit)'", 0)
	return rows.get(f"USD Loan - {COMPANY_SHORT_NAME}", 0), provisional


def create_account(account_name: str, parent_account: str, company: str, account_currency: str | None = None):
	if frappe.db.exists("Account", {"account_name": account_name, "company": company}):
		return

	acc = frappe.new_doc("Account")
	acc.account_name = account_name
	acc.company = COMPANY
	acc.parent_account = parent_account
	acc.account_currency = account_currency
	acc.insert()

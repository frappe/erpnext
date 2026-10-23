# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import flt
from frappe.utils.data import today

from erpnext.accounts.report.balance_sheet.balance_sheet import execute
from erpnext.accounts.report.financial_statements import build_period_list, is_dimension_grouped
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company 6"
COMPANY_SHORT_NAME = "_TC6"


class TestBalanceSheet(ERPNextTestSuite):
	def test_balance_sheet(self):
		create_account("VAT Liabilities", f"Duties and Taxes - {COMPANY_SHORT_NAME}", COMPANY)
		create_account("Advance VAT Paid", f"Duties and Taxes - {COMPANY_SHORT_NAME}", COMPANY)
		create_account("My Bank", f"Bank Accounts - {COMPANY_SHORT_NAME}", COMPANY)

		# 1000 equity paid to bank account
		make_journal_entry(
			[
				dict(
					account_name="My Bank",
					debit_in_account_currency=1000,
					credit_in_account_currency=0,
				),
				dict(
					account_name="Capital Stock",
					debit_in_account_currency=0,
					credit_in_account_currency=1000,
				),
			]
		)

		# 110 income paid to bank account (100 revenue + 10 VAT)
		make_journal_entry(
			[
				dict(
					account_name="My Bank",
					debit_in_account_currency=110,
					credit_in_account_currency=0,
				),
				dict(
					account_name="Sales",
					debit_in_account_currency=0,
					credit_in_account_currency=100,
				),
				dict(
					account_name="VAT Liabilities",
					debit_in_account_currency=0,
					credit_in_account_currency=10,
				),
			]
		)

		# offset VAT Liabilities with intra-year advance payment
		make_journal_entry(
			[
				dict(
					account_name="My Bank",
					debit_in_account_currency=0,
					credit_in_account_currency=10,
				),
				dict(
					account_name="Advance VAT Paid",
					debit_in_account_currency=10,
					credit_in_account_currency=0,
				),
			]
		)

		filters = frappe._dict(
			company=COMPANY,
			period_start_date=today(),
			period_end_date=today(),
			periodicity="Yearly",
		)
		results = execute(filters)
		name_and_total = {
			account_dict["account_name"]: account_dict["total"]
			for account_dict in results[1]
			if "total" in account_dict and "account_name" in account_dict
		}

		self.assertNotIn("Sales", name_and_total)

		self.assertIn("My Bank", name_and_total)
		self.assertEqual(name_and_total["My Bank"], 1100)

		self.assertIn("VAT Liabilities", name_and_total)
		self.assertEqual(name_and_total["VAT Liabilities"], 10)

		self.assertIn("Advance VAT Paid", name_and_total)
		self.assertEqual(name_and_total["Advance VAT Paid"], -10)

		self.assertIn("Duties and Taxes", name_and_total)
		self.assertEqual(name_and_total["Duties and Taxes"], 0)

		self.assertIn("Application of Funds (Assets)", name_and_total)
		self.assertEqual(name_and_total["Application of Funds (Assets)"], 1100)

		self.assertIn("Equity", name_and_total)
		self.assertEqual(name_and_total["Equity"], 1000)

		self.assertIn("'Provisional Profit / Loss (Credit)'", name_and_total)
		self.assertEqual(name_and_total["'Provisional Profit / Loss (Credit)'"], 100)

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

	def test_group_by_dimension(self):
		create_account("BS Dim Test Bank", f"Bank Accounts - {COMPANY_SHORT_NAME}", COMPANY)

		cc1 = frappe.db.get_value("Cost Center", {"company": COMPANY, "is_group": 0}, "name")
		parent_cc = frappe.db.get_value("Cost Center", {"company": COMPANY, "is_group": 1}, "name")

		cc2 = frappe.new_doc("Cost Center")
		cc2.cost_center_name = "BS Test CC 2"
		cc2.parent_cost_center = parent_cc
		cc2.company = COMPANY
		cc2.insert()

		make_journal_entry(
			[
				dict(
					account_name="BS Dim Test Bank",
					debit_in_account_currency=300,
					credit_in_account_currency=0,
					cost_center=cc1,
				),
				dict(
					account_name="Capital Stock",
					debit_in_account_currency=0,
					credit_in_account_currency=300,
					cost_center=cc1,
				),
			]
		)
		make_journal_entry(
			[
				dict(
					account_name="BS Dim Test Bank",
					debit_in_account_currency=500,
					credit_in_account_currency=0,
					cost_center=cc2.name,
				),
				dict(
					account_name="Capital Stock",
					debit_in_account_currency=0,
					credit_in_account_currency=500,
					cost_center=cc2.name,
				),
			]
		)

		filters = frappe._dict(
			company=COMPANY,
			period_start_date=today(),
			period_end_date=today(),
			periodicity="Yearly",
			filter_based_on="Date Range",
			accumulated_values=True,
			group_by_dimension="Cost Center",
		)
		period_list = build_period_list(filters)
		self.assertTrue(is_dimension_grouped(period_list))

		def key_for(cost_center):
			return next(p.key for p in period_list if p.dimension_value == cost_center)

		columns, data, *_ = execute(filters)

		# each dimension group starts with exactly one flagged column (UI boundary marker)
		first_flags = [c["dimension_value"] for c in columns if c.get("is_first_in_dimension")]
		self.assertEqual(len(first_flags), len(set(first_flags)))
		self.assertLessEqual({cc1, cc2.name}, set(first_flags))

		bank_row = next((r for r in data if r.get("account_name") == "BS Dim Test Bank"), None)
		self.assertIsNotNone(bank_row)
		self.assertEqual(bank_row[key_for(cc1)], 300)
		self.assertEqual(bank_row[key_for(cc2.name)], 500)
		self.assertEqual(bank_row["total"], 800)


def get_profit_loss_rows(filters):
	rows = {row.get("account"): flt(row.get("total")) for row in execute(frappe._dict(filters))[1]}
	return (
		rows.get("'Unclosed Fiscal Years Profit / Loss (Credit)'", 0),
		rows.get("'Provisional Profit / Loss (Credit)'", 0),
	)


def get_loan_and_provisional_profit(filters):
	rows = {row.get("account"): flt(row.get("total"), 2) for row in execute(frappe._dict(filters))[1]}
	provisional = rows.get("'Provisional Profit / Loss (Credit)'", 0)
	return rows.get(f"USD Loan - {COMPANY_SHORT_NAME}", 0), provisional


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


def create_account(account_name: str, parent_account: str, company: str, account_currency: str | None = None):
	if frappe.db.exists("Account", {"account_name": account_name, "company": company}):
		return

	acc = frappe.new_doc("Account")
	acc.account_name = account_name
	acc.company = COMPANY
	acc.parent_account = parent_account
	acc.account_currency = account_currency
	acc.insert()

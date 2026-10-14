# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils.data import add_years, today

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

	def test_unclosed_fiscal_years_split_by_dimension(self):
		"""An unclosed previous year must be split across dimension columns, not dropped."""
		create_account("BS Unclosed Test Bank", f"Bank Accounts - {COMPANY_SHORT_NAME}", COMPANY)

		parent_cc = frappe.db.get_value("Cost Center", {"company": COMPANY, "is_group": 1}, "name")
		cost_centers = []
		for name in ("BS Unclosed CC A", "BS Unclosed CC B"):
			cc = frappe.new_doc("Cost Center")
			cc.cost_center_name = name
			cc.parent_cost_center = parent_cc
			cc.company = COMPANY
			cc.insert()
			cost_centers.append(cc.name)
		cc_a, cc_b = cost_centers

		def book_sale(cost_center, amount, posting_date=None):
			make_journal_entry(
				[
					dict(
						account_name="BS Unclosed Test Bank",
						debit_in_account_currency=amount,
						credit_in_account_currency=0,
						cost_center=cost_center,
					),
					dict(
						account_name="Sales",
						debit_in_account_currency=0,
						credit_in_account_currency=amount,
						cost_center=cost_center,
					),
				],
				posting_date=posting_date,
			)

		# last year's profit, never closed
		last_year = add_years(today(), -1)
		book_sale(cc_a, 300, last_year)
		book_sale(cc_b, 500, last_year)

		# this year's profit
		book_sale(cc_a, 100)
		book_sale(cc_b, 100)

		# execute() rewrites period_start_date, so each run needs its own filters
		def make_filters(accumulated_values):
			return frappe._dict(
				company=COMPANY,
				period_start_date=today(),
				period_end_date=today(),
				periodicity="Yearly",
				filter_based_on="Date Range",
				accumulated_values=accumulated_values,
				group_by_dimension="Cost Center",
			)

		period_list = build_period_list(make_filters(True))

		def key_for(cost_center):
			return next(p.key for p in period_list if p.dimension_value == cost_center)

		def find_row(data, name):
			return next((r for r in data if name in str(r.get("account_name", ""))), None)

		def values(row):
			# (CC A, CC B, Total), as the report shows them
			return (row[key_for(cc_a)], row[key_for(cc_b)], row["total"])

		# Accumulated: last year gets its own row, Provisional keeps only this year
		_columns, data, message, *_ = execute(make_filters(True))
		self.assertEqual(message, "Previous Financial Year is not closed")

		unclosed = find_row(data, "Unclosed Fiscal Years")
		self.assertIsNotNone(unclosed)
		self.assertEqual(values(unclosed), (300, 500, 800))
		self.assertEqual(values(find_row(data, "Provisional Profit / Loss")), (100, 100, 200))

		# Not accumulated: columns are this year's movement only, nothing to split out
		_columns, data, message, *_ = execute(make_filters(False))
		self.assertEqual(message, "Previous Financial Year is not closed")
		self.assertIsNone(find_row(data, "Unclosed Fiscal Years"))
		self.assertEqual(values(find_row(data, "Provisional Profit / Loss")), (100, 100, 200))


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


def create_account(account_name: str, parent_account: str, company: str):
	if frappe.db.exists("Account", {"account_name": account_name, "company": company}):
		return

	acc = frappe.new_doc("Account")
	acc.account_name = account_name
	acc.company = COMPANY
	acc.parent_account = parent_account
	acc.insert()

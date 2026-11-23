# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Consolidated reports, Profitability Analysis, Dimension-wise Accounts Balance, Financial Ratios,
and the dashboard chart on the cash basis (phase 6), with CB-28."""

import frappe
from frappe.utils import flt

from erpnext.accounts.cash_basis.tests.fixtures import (
	CUSTOMER,
	CUSTOMER_2,
	US_COMPANY,
	acc,
	get_or_create_company,
	set_company_method,
)
from erpnext.accounts.cash_basis.tests.report_case import ReportTestCase, comparable, report_values
from erpnext.accounts.cash_basis.tests.vouchers import (
	line,
	make_advance,
	make_journal_entry,
	make_sales_invoice,
	pay,
)
from erpnext.accounts.report.consolidated_financial_statement import consolidated_financial_statement
from erpnext.accounts.report.consolidated_trial_balance import consolidated_trial_balance
from erpnext.accounts.report.dimension_wise_accounts_balance_report import (
	dimension_wise_accounts_balance_report,
)
from erpnext.accounts.report.financial_ratios import financial_ratios
from erpnext.accounts.report.profit_and_loss_statement import profit_and_loss_statement
from erpnext.accounts.report.profitability_analysis import profitability_analysis

TAX = acc("ST 6%")
GROUP, GROUP_ABBR = "_Test Cash Basis Group", "_TCBG"
CHILD, CHILD_ABBR = "_Test Cash Basis Child", "_TCBK"


class TestCashBasisPhase6Reports(ReportTestCase):
	def setUp(self):
		super().setUp()
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-04-10", 55)
		self.fiscal_year = frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"})

	def year_filters(self, **extra):
		return frappe._dict(
			company=US_COMPANY,
			fiscal_year=self.fiscal_year,
			from_fiscal_year=self.fiscal_year,
			to_fiscal_year=self.fiscal_year,
			from_date="2026-01-01",
			to_date="2026-12-31",
			period_start_date="2026-01-01",
			period_end_date="2026-12-31",
			filter_based_on="Fiscal Year",
			periodicity="Yearly",
			**extra,
		)

	def both(self, execute, **extra):
		return {m: execute(self.year_filters(accounting_method=m, **extra)) for m in ("Accrual", "Cash")}

	def test_profitability_analysis(self):
		results = self.both(profitability_analysis.execute, based_on="Cost Center")
		main = {
			m: next(r for r in result[1] if r and r.get("account") == acc("Main"))
			for m, result in results.items()
		}
		self.assertEqual((main["Accrual"]["income"], main["Cash"]["income"]), (100, 50))

	def test_dimension_wise_accounts_balance(self):
		results = self.both(dimension_wise_accounts_balance_report.execute, dimension="Cost Center")
		sales = {
			m: next(r for r in result[1] if r and r.get("account") == acc("Sales"))
			for m, result in results.items()
		}
		key = frappe.scrub(acc("Main"))
		self.assertEqual((flt(sales["Accrual"][key]), flt(sales["Cash"][key])), (-100, -50))

	def test_financial_ratios(self):
		results = self.both(financial_ratios.execute)
		turnover = {
			m: next(r for r in result[1] if r and r.get("ratio") == "Debtor Turnover Ratio")
			for m, result in results.items()
		}
		# Accrual: 100 / ((55 + 0) / 2). Cash: 50 / ((5 + 0) / 2).
		self.assertEqual(
			(flt(turnover["Accrual"]["dec_2026"]), flt(turnover["Cash"]["dec_2026"])), (3.64, 20)
		)

	def test_consolidated_statement_of_one_company(self):
		results = self.both(consolidated_financial_statement.execute, report="Profit and Loss Statement")
		sales = {
			m: next(r for r in result[1] if r and r.get("account_name") == "Sales")
			for m, result in results.items()
		}
		self.assertEqual((sales["Accrual"]["total"], sales["Cash"]["total"]), (100, 50))
		self.assertIn("Accounting Method: Cash", results["Cash"][2])

	def test_dashboard_chart_uses_the_company_default(self):
		# The chart runs the Profit and Loss Statement with no method filter.
		chart_filters = frappe._dict(
			company=US_COMPANY,
			filter_based_on="Fiscal Year",
			from_fiscal_year=self.fiscal_year,
			to_fiscal_year=self.fiscal_year,
			period_start_date="2026-01-01",
			period_end_date="2026-12-31",
			periodicity="Yearly",
			include_default_book_entries=1,
		)
		self.assertEqual(report_values(profit_and_loss_statement.execute(chart_filters), acc("Sales")), 50)

	def test_accrual_output_is_identical(self):
		reports = (
			(profitability_analysis.execute, {"based_on": "Cost Center"}),
			(dimension_wise_accounts_balance_report.execute, {"dimension": "Cost Center"}),
			(financial_ratios.execute, {}),
			(consolidated_financial_statement.execute, {"report": "Profit and Loss Statement"}),
			(consolidated_financial_statement.execute, {"report": "Balance Sheet"}),
		)
		set_company_method(US_COMPANY, "Accrual")
		before = [comparable(execute(self.year_filters(**extra))) for execute, extra in reports]
		set_company_method(US_COMPANY, "Cash")
		after = [
			comparable(execute(self.year_filters(accounting_method="Accrual", **extra)))
			for execute, extra in reports
		]
		self.assertEqual(before, after)


class TestCashBasisGroupCompany(ReportTestCase):
	"""CB-28: a consolidated statement with a parent and a subsidiary."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		get_or_create_company(GROUP, GROUP_ABBR, is_group=1)
		get_or_create_company(CHILD, CHILD_ABBR, parent=GROUP)

	def setUp(self):
		super().setUp()
		set_company_method(GROUP, "Cash")
		set_company_method(CHILD, "Cash")
		self.fiscal_year = frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"})
		child_invoice = make_sales_invoice(
			"2026-03-01",
			[line(100, account=f"Sales - {CHILD_ABBR}", cost_center=f"Main - {CHILD_ABBR}")],
			company=CHILD,
			debit_to=f"Debtors - {CHILD_ABBR}",
			cost_center=f"Main - {CHILD_ABBR}",
		)
		pay(child_invoice, "2026-04-10", 40, bank=f"Cash - {CHILD_ABBR}")
		make_sales_invoice(
			"2026-03-02",
			[line(50, account=f"Sales - {GROUP_ABBR}", cost_center=f"Main - {GROUP_ABBR}")],
			company=GROUP,
			debit_to=f"Debtors - {GROUP_ABBR}",
			cost_center=f"Main - {GROUP_ABBR}",
		)

	def statement(self, method, report="Profit and Loss Statement"):
		return consolidated_financial_statement.execute(
			frappe._dict(
				company=GROUP,
				report=report,
				filter_based_on="Fiscal Year",
				from_fiscal_year=self.fiscal_year,
				to_fiscal_year=self.fiscal_year,
				period_start_date="2026-01-01",
				period_end_date="2026-12-31",
				periodicity="Yearly",
				accounting_method=method,
			)
		)

	def test_cb28_consolidated_profit_and_loss(self):
		accrual, cash = self.statement("Accrual"), self.statement("Cash")
		accrual_sales = next(r for r in accrual[1] if r and r.get("account_name") == "Sales")
		cash_sales = next(r for r in cash[1] if r and r.get("account_name") == "Sales")
		self.assertEqual(accrual_sales["total"], 150)
		# The subsidiary received 40. The parent received nothing.
		self.assertEqual((cash_sales[CHILD], cash_sales[GROUP], cash_sales["total"]), (40, 0, 40))

	def test_each_company_keeps_its_unapplied_treatment(self):
		# Open point 13. An unallocated receipt of 30 in each company. The parent shows unapplied
		# cash as income, the subsidiary keeps it on the balance sheet.
		set_company_method(GROUP, "Cash", "Income and Expense")
		set_company_method(CHILD, "Cash", "Balance Sheet")
		for company, abbr in ((GROUP, GROUP_ABBR), (CHILD, CHILD_ABBR)):
			make_advance(
				"Customer",
				CUSTOMER,
				"2026-05-01",
				30,
				bank=f"Cash - {abbr}",
				party_account=f"Debtors - {abbr}",
				company=company,
			)
		cash = self.statement("Cash")
		unapplied = [r for r in cash[1] if r and r.get("account_name") == "Unapplied Cash Receipts"]
		self.assertEqual([(flt(r[GROUP]), flt(r[CHILD])) for r in unapplied], [(30, 0)])

	def test_cb28_consolidated_balance_sheet_balances(self):
		cash = self.statement("Cash", report="Balance Sheet")
		profit = next(r for r in cash[1] if r and "Provisional Profit" in str(r.get("account_name")))
		self.assertEqual(flt(profit["total"]), 40)

	def test_cb28_consolidated_trial_balance(self):
		def run(method):
			return consolidated_trial_balance.execute(
				frappe._dict(
					company=[GROUP],
					fiscal_year=self.fiscal_year,
					from_date="2026-01-01",
					to_date="2026-12-31",
					accounting_method=method,
				)
			)

		cash = run("Cash")
		sales = next(
			r for r in cash[1] if r and str(r.get("account_name") or r.get("account")).startswith("Sales")
		)
		self.assertEqual(flt(sales["closing_credit"]) - flt(sales["closing_debit"]), 40)
		total = cash[1][-1]
		self.assertEqual(flt(total["closing_debit"]), flt(total["closing_credit"]))


FX_GROUP, EUR_CHILD, CA_CHILD = (
	"_Test Cash Basis Group FX",
	"_Test Cash Basis Child EUR",
	"_Test Cash Basis Child CA",
)
ABBRS = {FX_GROUP: "_TCBX", EUR_CHILD: "_TCBE", CA_CHILD: "_TCBA"}


class TestCashBasisMixedCurrencyGroup(ReportTestCase):
	"""A parent in USD, a child in EUR (1 EUR = 1.2 USD), and a child in Canada, outside the scope."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		get_or_create_company(FX_GROUP, ABBRS[FX_GROUP], is_group=1)
		get_or_create_company(EUR_CHILD, ABBRS[EUR_CHILD], currency="EUR", parent=FX_GROUP)
		get_or_create_company(CA_CHILD, ABBRS[CA_CHILD], country="Canada", parent=FX_GROUP)

	def setUp(self):
		super().setUp()
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": "2025-01-01",
				"from_currency": "EUR",
				"to_currency": "USD",
				"exchange_rate": 1.2,
				"for_buying": 1,
				"for_selling": 1,
			}
		).insert()
		set_company_method(FX_GROUP, "Cash")
		set_company_method(EUR_CHILD, "Cash")
		self.fiscal_year = frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"})
		invoice = self.invoice(EUR_CHILD, "2026-03-01", 100)
		pay(invoice, "2026-04-10", 40, bank=f"Cash - {ABBRS[EUR_CHILD]}")
		self.invoice(EUR_CHILD, "2026-03-05", 30)
		self.invoice(CA_CHILD, "2026-03-02", 70)

	def invoice(self, company, posting_date, amount):
		abbr = ABBRS[company]
		return make_sales_invoice(
			posting_date,
			[line(amount, account=f"Sales - {abbr}", cost_center=f"Main - {abbr}")],
			company=company,
			debit_to=f"Debtors - {abbr}",
			cost_center=f"Main - {abbr}",
			currency=frappe.get_cached_value("Company", company, "default_currency"),
			conversion_rate=1,
		)

	def trial_balance(self, from_date="2026-01-01", **extra):
		return consolidated_trial_balance.execute(
			frappe._dict(
				company=[FX_GROUP, EUR_CHILD, CA_CHILD],
				fiscal_year=self.fiscal_year,
				from_date=from_date,
				to_date="2026-12-31",
				**extra,
			)
		)

	def net(self, result, prefix, side="closing"):
		row = next(r for r in result[1] if r and str(r.get("account")).startswith(prefix))
		return flt(row[f"{side}_credit"] - row[f"{side}_debit"], 2)

	def assert_balanced(self, result):
		total = result[1][-1]
		self.assertEqual(flt(total["closing_debit"], 2), flt(total["closing_credit"], 2))
		self.assertEqual(flt(total["opening_debit"], 2), flt(total["opening_credit"], 2))

	def test_trial_balance_in_the_reporting_currency(self):
		cash = self.trial_balance(accounting_method="Cash")
		# 40 EUR received x 1.2, and 70 of the Canada child, which stays on accrual.
		self.assertEqual(self.net(cash, "Sales"), 118)
		self.assertEqual(self.net(cash, "Debtors"), -70)
		self.assert_balanced(cash)
		self.assertIn("Accounting Method: Cash", cash[2])

	def test_trial_balance_opening_in_a_presentation_currency(self):
		cash = self.trial_balance("2026-07-01", accounting_method="Cash", presentation_currency="EUR")
		# The opening converts one time: 70 USD / 1.2, and 40 EUR + 70 USD / 1.2.
		self.assertEqual(self.net(cash, "Debtors", "opening"), -58.33)
		self.assertEqual(self.net(cash, "Sales", "opening"), 98.33)
		self.assertEqual(self.net(cash, "Debtors", "opening"), self.net(cash, "Debtors"))
		self.assert_balanced(cash)
		# The EUR child converts its adjustment rows to USD one time only: 40 x 1.2 + 70.
		cash = self.trial_balance("2026-07-01", accounting_method="Cash", presentation_currency="USD")
		self.assertEqual(self.net(cash, "Sales", "opening"), 118)
		self.assertEqual(self.net(cash, "Debtors", "opening"), -70)
		self.assert_balanced(cash)

	def test_trial_balance_takes_the_method_of_the_first_company(self):
		set_company_method(FX_GROUP, "Accrual")
		result = self.trial_balance()
		self.assertEqual(self.net(result, "Sales"), 226)
		self.assertIn("Accounting Method: Accrual", result[2])

	def test_consolidated_statement_keeps_a_company_outside_the_scope_on_accrual(self):
		def statement(report):
			return consolidated_financial_statement.execute(
				frappe._dict(
					company=FX_GROUP,
					report=report,
					filter_based_on="Fiscal Year",
					from_fiscal_year=self.fiscal_year,
					to_fiscal_year=self.fiscal_year,
					period_start_date="2026-01-01",
					period_end_date="2026-12-31",
					periodicity="Yearly",
					accounting_method="Cash",
				)
			)

		sales = next(
			r for r in statement("Profit and Loss Statement")[1] if r and r.get("account_name") == "Sales"
		)
		self.assertEqual((sales[EUR_CHILD], sales[CA_CHILD], sales["total"]), (40, 70, 110))
		balance_sheet = statement("Balance Sheet")
		rows = {str(r.get("account_name")): r for r in balance_sheet[1] if r}
		self.assertEqual(rows["'Total Asset (Debit)'"]["total"], rows["'Total (Credit)'"]["total"])
		self.assertIn("Accounting Method: Cash", balance_sheet[2])

	def test_trial_balance_accrual_output_is_identical(self):
		set_company_method(FX_GROUP, "Accrual")
		set_company_method(EUR_CHILD, "Accrual")
		before = [
			comparable(self.trial_balance()),
			comparable(self.trial_balance("2026-07-01", presentation_currency="EUR")),
		]
		set_company_method(FX_GROUP, "Cash")
		set_company_method(EUR_CHILD, "Cash")
		after = [
			comparable(self.trial_balance(accounting_method="Accrual")),
			comparable(
				self.trial_balance("2026-07-01", accounting_method="Accrual", presentation_currency="EUR")
			),
		]
		self.assertEqual(before, after)

	def test_message_lists_the_exceptions_of_each_company(self):
		abbr = ABBRS[EUR_CHILD]
		journal = make_journal_entry(
			"2026-03-01",
			[
				{"account": f"Debtors - {abbr}", "debit": 50, "party_type": "Customer", "party": CUSTOMER},
				{"account": f"Debtors - {abbr}", "debit": 50, "party_type": "Customer", "party": CUSTOMER_2},
				{"account": f"Sales - {abbr}", "credit": 100},
			],
			company=EUR_CHILD,
		)
		for row in journal.accounts:
			self.assertEqual(row.cost_center, f"Main - {abbr}")
		statement = consolidated_financial_statement.execute(
			frappe._dict(
				company=FX_GROUP,
				report="Profit and Loss Statement",
				filter_based_on="Fiscal Year",
				from_fiscal_year=self.fiscal_year,
				to_fiscal_year=self.fiscal_year,
				period_start_date="2026-01-01",
				period_end_date="2026-12-31",
				periodicity="Yearly",
				accounting_method="Cash",
			)
		)
		for message in (statement[2], self.trial_balance(accounting_method="Cash")[2]):
			# One line for the EUR child, in its own currency, and a button to its reconciliation.
			self.assertIn(f"{frappe.bold(EUR_CHILD)}: 1 voucher needs review", message)
			self.assertIn(f">Review {EUR_CHILD}</a>", message)
			self.assertIn(frappe.utils.fmt_money(100, currency="EUR"), message)
			self.assertIn(frappe.utils.quote(EUR_CHILD), message)
			self.assertNotIn(frappe.bold(FX_GROUP), message)

	def test_reporting_rate_is_the_rate_of_the_payment_date(self):
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": "2026-06-01",
				"from_currency": "EUR",
				"to_currency": "USD",
				"exchange_rate": 1.1,
				"for_buying": 1,
				"for_selling": 1,
			}
		).insert()
		invoice = self.invoice(EUR_CHILD, "2026-05-01", 50)
		pay(invoice, "2026-06-10", bank=f"Cash - {ABBRS[EUR_CHILD]}")
		cash = self.trial_balance(accounting_method="Cash")
		# The income is the cash received: 40 x 1.2, 50 x 1.1, and 70 of the Canada child.
		self.assertEqual(self.net(cash, "Sales"), 173)
		self.assertEqual(self.net(cash, "Debtors"), -70)
		self.assert_balanced(cash)

	def test_two_rates_on_one_date(self):
		self.invoice(EUR_CHILD, "2026-05-01", 50)
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": "2026-05-01",
				"from_currency": "EUR",
				"to_currency": "USD",
				"exchange_rate": 1.25,
				"for_buying": 1,
				"for_selling": 1,
			}
		).insert()
		self.invoice(EUR_CHILD, "2026-05-01", 20)
		rates = frappe.get_all(
			"GL Entry",
			filters={"company": EUR_CHILD, "posting_date": "2026-05-01"},
			pluck="reporting_currency_exchange_rate",
			distinct=True,
		)
		self.assertEqual(sorted(rates), [1.2, 1.25])
		cash = self.trial_balance(accounting_method="Cash")
		# The two invoices are not paid, so each one is removed at its own rate.
		self.assertEqual(self.net(cash, "Sales"), 118)
		self.assertEqual(self.net(cash, "Debtors"), -70)
		self.assert_balanced(cash)

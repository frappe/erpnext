# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Trial Balance, Cash Flow and the Financial Report Template engine on the cash basis (phase 4)."""

import frappe
from frappe.utils import flt

from erpnext.accounts.cash_basis.tests.fixtures import US_COMPANY, acc, set_company_method
from erpnext.accounts.cash_basis.tests.report_case import ReportTestCase, comparable
from erpnext.accounts.cash_basis.tests.vouchers import line, make_sales_invoice, pay
from erpnext.accounts.report.balance_sheet import balance_sheet
from erpnext.accounts.report.cash_flow import cash_flow
from erpnext.accounts.report.profit_and_loss_statement import profit_and_loss_statement
from erpnext.accounts.report.trial_balance import trial_balance
from erpnext.tests.utils import change_settings

SALES = acc("Sales")
DEBTORS = acc("Debtors")
TAX = acc("ST 6%")
BANK = acc("Test Bank")
RETAINED = acc("Retained Earnings")


class TestCashBasisPhase4Reports(ReportTestCase):
	def setUp(self):
		super().setUp()
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-04-10", 55)
		self.fiscal_year = frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"})

	def trial_balance(self, from_date="2026-01-01", to_date="2026-12-31", **extra):
		filters = frappe._dict(
			company=US_COMPANY, fiscal_year=self.fiscal_year, from_date=from_date, to_date=to_date, **extra
		)
		return trial_balance.execute(filters)

	def tb_row(self, result, account):
		return next(row for row in result[1] if row and row.get("account") == account)

	def tb_net(self, result, account, column):
		"""Debit less credit of a column pair: the report shows gross values without show_net_values."""
		row = self.tb_row(result, account)
		return flt(
			flt(row[f"{column}_debit" if column else "debit"])
			- flt(row[f"{column}_credit" if column else "credit"]),
			2,
		)

	def test_trial_balance_on_cash_basis(self):
		accrual = self.trial_balance(accounting_method="Accrual")
		cash = self.trial_balance()
		self.assertEqual(self.tb_net(accrual, SALES, "closing"), -100)
		# Section 6.5 example: income 50, receivable 5, tax 10, bank 55.
		expected = {SALES: -50, DEBTORS: 5, TAX: -10, BANK: 55}
		for account, balance in expected.items():
			self.assertEqual(self.tb_net(cash, account, "closing"), balance, account)
		# I1: the cash basis Trial Balance balances.
		total = next(row for row in cash[1] if row and "Total" in str(row.get("account")))
		self.assertEqual(flt(total["debit"]), flt(total["credit"]))
		self.assertEqual(flt(total["closing_debit"]), flt(total["closing_credit"]))

	def calculation_dates(self, filters):
		"""The dates of the calculations that one report run kept: one run, at the report end."""
		from erpnext.accounts.cash_basis.reports import CACHE_KEY

		cache = filters.get(CACHE_KEY) or {}
		results = [key for key in cache if isinstance(key, tuple) and key[0] == "result"]
		return [str(cache["date"])] * len(results)

	def slice_end_dates(self, filters):
		"""The end dates of the slices in the cache. A second calculation clears the cache,
		so the slices of every period stay only when the run calculated once."""
		from erpnext.accounts.cash_basis.reports import CACHE_KEY

		return {
			key[3] for key in (filters.get(CACHE_KEY) or {}) if isinstance(key, tuple) and key[0] == "entries"
		}

	def test_one_calculation_for_each_report_run(self):
		filters = self.report_filters("2026-01-01", "2026-12-31", periodicity="Monthly")
		cash_flow.execute(filters)
		self.assertEqual(self.calculation_dates(filters), ["2026-12-31"])
		month_ends = {str(frappe.utils.get_last_day(f"2026-{month:02d}-01")) for month in range(1, 13)}
		self.assertTrue(month_ends <= self.slice_end_dates(filters), "a slice for each month survives")

		filters = frappe._dict(
			company=US_COMPANY, fiscal_year=self.fiscal_year, from_date="2026-04-01", to_date="2026-10-31"
		)
		trial_balance.execute(filters)
		self.assertEqual(self.calculation_dates(filters), ["2026-10-31"])
		self.assertTrue({"2026-03-31", "2026-10-31"} <= self.slice_end_dates(filters))

		filters = self.report_filters(
			"2026-04-01", "2026-06-30", report_template="Standard Balance Sheet (IFRS)", accumulated_values=1
		)
		balance_sheet.execute(filters)
		self.assertEqual(self.calculation_dates(filters), ["2026-06-30"])

	def test_fiscal_year_mode_uses_the_selected_years(self):
		# The page sets a hidden period_end_date that does not match the selected years.
		filters = self.report_filters(
			"2026-01-01",
			"2027-12-31",
			filter_based_on="Fiscal Year",
			from_fiscal_year=self.fiscal_year,
			to_fiscal_year=self.fiscal_year,
		)
		result = profit_and_loss_statement.execute(filters)
		self.assertEqual(self.calculation_dates(filters), ["2026-12-31"])
		sales = next(row for row in result[1] if row and row.get("account") == SALES)
		self.assertEqual(flt(sales["total"]), 50)

	def test_trial_balance_and_cash_flow_show_the_message(self):
		self.assertIn("Accounting Method: Cash", self.trial_balance()[2])
		result = self.run_report(cash_flow.execute, "2026-01-01", "2026-12-31")
		self.assertIn("Accounting Method: Cash", result[2])

	def test_monthly_cash_flow_matches_the_bank(self):
		result = self.run_report(cash_flow.execute, "2026-01-01", "2026-12-31", periodicity="Monthly")
		row = next(
			r
			for r in result[1]
			if r and "Net Change in Cash" in str(r.get("section_name") or r.get("section"))
		)
		self.assertEqual((flt(row.get("mar_2026")), flt(row.get("apr_2026"))), (0, 55))
		receivable = next(r for r in result[1] if r and "Accounts Receivable" in str(r.get("section_name")))
		# March: the deferred invoice moves nothing on the cash basis. April: 55 paid, 50 income.
		self.assertEqual((flt(receivable.get("mar_2026")), flt(receivable.get("apr_2026"))), (-10, 5))

	def test_trial_balance_opening_on_cash_basis(self):
		cash = self.trial_balance(from_date="2026-04-01")
		# March: the invoice is deferred. The P&L opening starts at the year start.
		self.assertEqual(self.tb_net(cash, SALES, "opening"), 0)
		self.assertEqual(self.tb_net(cash, SALES, None), -50)
		self.assertEqual(self.tb_net(cash, DEBTORS, "opening"), 10)
		self.assertEqual(self.tb_net(cash, DEBTORS, "closing"), 5)

	def test_trial_balance_accrual_output_is_identical(self):
		set_company_method(US_COMPANY, "Accrual")
		before = comparable(self.trial_balance())
		set_company_method(US_COMPANY, "Cash")
		self.assertEqual(before, comparable(self.trial_balance(accounting_method="Accrual")))

	def test_trial_balance_snapshot_falls_back_with_cash(self):
		filters = frappe._dict(
			company=US_COMPANY, fiscal_year=self.fiscal_year, from_date="2026-01-01", to_date="2026-12-31"
		)
		result = trial_balance.execute_snapshot_report(filters)
		self.assertEqual(self.tb_net(result, SALES, "closing"), -50)

	def cash_flow_value(self, result, label):
		row = next(
			row for row in result[1] if row and label in str(row.get("section_name") or row.get("section"))
		)
		return flt(row.get("total"), 2)

	def test_cash_flow_on_cash_basis(self):
		accrual = self.run_report(cash_flow.execute, "2026-01-01", "2026-12-31", accounting_method="Accrual")
		cash = self.run_report(cash_flow.execute, "2026-01-01", "2026-12-31")
		self.assertEqual(self.cash_flow_value(accrual, "Net Change in Accounts Receivable"), -55)
		self.assertEqual(self.cash_flow_value(cash, "Net Change in Accounts Receivable"), -5)
		self.assertEqual(self.cash_flow_value(accrual, "Profit for the year"), 100)
		self.assertEqual(self.cash_flow_value(cash, "Profit for the year"), 50)
		# The bank rows do not change: the net change in cash is 55 in both methods.
		for result in (accrual, cash):
			self.assertEqual(self.cash_flow_value(result, "Net Change in Cash"), 55)

	def test_cash_flow_accrual_output_is_identical(self):
		set_company_method(US_COMPANY, "Accrual")
		before = comparable(self.run_report(cash_flow.execute, "2026-01-01", "2026-12-31"))
		set_company_method(US_COMPANY, "Cash")
		after = comparable(
			self.run_report(cash_flow.execute, "2026-01-01", "2026-12-31", accounting_method="Accrual")
		)
		self.assertEqual(before, after)

	def template_values(self, accounting_method):
		template = "Standard Profit and Loss (IFRS)"
		self.assertTrue(
			frappe.db.exists("Financial Report Template", template), "the template ships as a fixture"
		)
		result = self.run_report(
			profit_and_loss_statement.execute,
			"2026-01-01",
			"2026-12-31",
			report_template=template,
			accounting_method=accounting_method,
		)
		return result[1]

	def test_balance_sheet_template_on_cash_basis(self):
		template = "Standard Balance Sheet (IFRS)"
		self.assertTrue(frappe.db.exists("Financial Report Template", template))
		results = {}
		for method in ("Accrual", "Cash"):
			results[method] = balance_sheet.execute(
				self.report_filters(
					"2026-01-01",
					"2026-04-30",
					report_template=template,
					accounting_method=method,
					accumulated_values=1,
				)
			)
		pairs = set()
		for accrual_row, cash_row in zip(results["Accrual"][1], results["Cash"][1], strict=True):
			for key, value in (accrual_row or {}).items():
				if isinstance(value, int | float) and isinstance(cash_row.get(key), int | float):
					pairs.add((flt(value, 2), flt(cash_row[key], 2)))
		# The receivable: 55 on accrual, 5 on cash (section 6.5 example).
		self.assertIn((55.0, 5.0), pairs)
		self.assertIn("receivables and payables show only the tax of unpaid invoices", results["Cash"][2])

	def test_balance_sheet_template_with_an_opening(self):
		results = {}
		for method in ("Accrual", "Cash"):
			results[method] = balance_sheet.execute(
				self.report_filters(
					"2026-04-01",
					"2026-04-30",
					report_template="Standard Balance Sheet (IFRS)",
					accounting_method=method,
					accumulated_values=1,
				)
			)
		pairs = set()
		for accrual_row, cash_row in zip(results["Accrual"][1], results["Cash"][1], strict=True):
			for key, value in (accrual_row or {}).items():
				if isinstance(value, int | float) and isinstance(cash_row.get(key), int | float):
					pairs.add((flt(value, 2), flt(cash_row[key], 2)))
		# The opening of April holds the March invoice: the closing receivable is 55 and 5.
		self.assertIn((55.0, 5.0), pairs)
		self.assertIn("Accounting Method: Cash", results["Cash"][2])

	def test_trial_balance_presentation_currency(self):
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": "2026-01-01",
				"from_currency": "USD",
				"to_currency": "EUR",
				"exchange_rate": 0.5,
				"for_buying": 1,
				"for_selling": 1,
			}
		).insert()
		cash = self.trial_balance(presentation_currency="EUR")
		self.assertEqual(self.tb_net(cash, SALES, "closing"), -25)
		opening = self.trial_balance(from_date="2026-04-01", presentation_currency="EUR")
		self.assertEqual(self.tb_net(opening, DEBTORS, "opening"), 5)

	def test_trial_balance_with_user_permission(self):
		user = "test-cash-basis-tb@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Cash Basis TB",
					"roles": [{"role": "Accounts User"}, {"role": "Accounts Manager"}],
				}
			).insert()
		invoice = make_sales_invoice(
			"2026-03-01",
			[
				line(60, account=SALES, cost_center=acc("Main")),
				line(40, account=acc("Service"), cost_center=acc("Second")),
			],
		)
		pay(invoice, "2026-04-10", 50)
		for allow, value in (("Company", US_COMPANY), ("Cost Center", acc("Main"))):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user,
					"allow": allow,
					"for_value": value,
					"apply_to_all_doctypes": 1,
				}
			).insert()
		with self.set_user(user):
			result = self.trial_balance()
		# CB-04 gives 50 on Sales (Main); this invoice adds 30 of its Main line. Service is hidden.
		self.assertEqual(self.tb_net(result, SALES, "closing"), -80)
		self.assertFalse(
			[
				r
				for r in result[1]
				if r and r.get("account") == acc("Service") and flt(r.get("closing_credit"))
			]
		)

	def test_cash_flow_grouped_by_dimension_keeps_the_totals(self):
		make_sales_invoice("2026-03-02", [line(30)], cost_center=None)
		label = "Net Change in Accounts Receivable"
		values = {}
		for method in ("Accrual", "Cash"):
			for grouping in (None, "Cost Center"):
				result = self.run_report(
					cash_flow.execute,
					"2026-01-01",
					"2026-12-31",
					accounting_method=method,
					group_by_dimension=grouping,
				)
				values[(method, grouping)] = self.cash_flow_value(result, label)
		# I8: the cash adjustments are the same with and without the group-by. The pair carries the
		# cost center of the line, so a blank receivable row and its adjustment can sit in two columns.
		self.assertEqual(
			values[("Cash", "Cost Center")] - values[("Accrual", "Cost Center")],
			values[("Cash", None)] - values[("Accrual", None)],
		)

	def test_report_template_on_cash_basis(self):
		accrual = self.template_values("Accrual")
		cash = self.template_values("Cash")
		pairs = set()
		for accrual_row, cash_row in zip(accrual, cash, strict=True):
			for key, value in (accrual_row or {}).items():
				if isinstance(value, int | float) and isinstance(cash_row.get(key), int | float):
					pairs.add((flt(value, 2), flt(cash_row[key], 2)))
		self.assertIn((100.0, 50.0), pairs, "a revenue row shows 100 on accrual and 50 on cash")
		self.assertNotEqual(comparable((None, accrual)), comparable((None, cash)))


class TestCashBasisPhase4Closing(ReportTestCase):
	@change_settings("Accounts Settings", {"use_legacy_controller_for_pcv": 1})
	def test_cb25_through_trial_balance_and_cash_flow(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": "2026-12-31",
				"period_start_date": "2026-01-01",
				"period_end_date": "2026-12-31",
				"company": US_COMPANY,
				"fiscal_year": frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"}),
				"cost_center": acc("Main"),
				"closing_account_head": RETAINED,
				"remarks": "Cash basis test",
			}
		).insert().submit()
		pay(invoice, "2027-02-10")
		fiscal_year = frappe.db.get_value("Fiscal Year", {"year_start_date": "2027-01-01"})

		def run(method):
			return trial_balance.execute(
				frappe._dict(
					company=US_COMPANY,
					fiscal_year=fiscal_year,
					from_date="2027-01-01",
					to_date="2027-12-31",
					with_period_closing_entry_for_opening=1,
					accounting_method=method,
				)
			)

		def net(result, account, column):
			row = next(r for r in result[1] if r and r.get("account") == account)
			return flt(flt(row[f"{column}_debit"]) - flt(row[f"{column}_credit"]), 2)

		accrual, cash = run("Accrual"), run("Cash")
		# The opening comes from the closing balances of the PCV. The cash basis closed 0 of profit.
		self.assertEqual(net(accrual, RETAINED, "opening"), -100)
		self.assertEqual(net(cash, RETAINED, "opening"), 0)
		self.assertEqual(net(accrual, DEBTORS, "opening"), 100)
		self.assertEqual(net(cash, DEBTORS, "opening"), 0)
		self.assertEqual(net(cash, SALES, "closing"), -100)
		total = next(r for r in cash[1] if r and "Total" in str(r.get("account")))
		self.assertEqual(flt(total["closing_debit"]), flt(total["closing_credit"]))

		# The flag off: the closing balance of Sales holds its full history to the PCV.
		without_flag = trial_balance.execute(
			frappe._dict(
				company=US_COMPANY,
				fiscal_year=fiscal_year,
				from_date="2027-01-01",
				to_date="2027-12-31",
				with_period_closing_entry_for_opening=0,
				accounting_method="Cash",
			)
		)
		self.assertEqual(net(without_flag, SALES, "opening"), 0)
		self.assertEqual(net(without_flag, SALES, "closing"), -100)
		total = next(r for r in without_flag[1] if r and "Total" in str(r.get("account")))
		self.assertEqual(flt(total["opening_debit"]), flt(total["opening_credit"]))
		self.assertEqual(flt(total["closing_debit"]), flt(total["closing_credit"]))

		# A from date in the middle of the year after the PCV, with the flag on and off.
		for flag in (0, 1):
			mid_year = trial_balance.execute(
				frappe._dict(
					company=US_COMPANY,
					fiscal_year=fiscal_year,
					from_date="2027-04-01",
					to_date="2027-12-31",
					with_period_closing_entry_for_opening=flag,
					accounting_method="Cash",
				)
			)
			# The payment of February is income before April.
			self.assertEqual(net(mid_year, SALES, "opening"), -100, f"flag {flag}")
			total = next(r for r in mid_year[1] if r and "Total" in str(r.get("account")))
			self.assertEqual(flt(total["opening_debit"]), flt(total["opening_credit"]), f"flag {flag}")
			self.assertEqual(flt(total["closing_debit"]), flt(total["closing_credit"]), f"flag {flag}")

		flow = self.run_report(cash_flow.execute, "2027-01-01", "2027-12-31")
		profit = next(
			r
			for r in flow[1]
			if r and "Profit for the year" in str(r.get("section_name") or r.get("section"))
		)
		self.assertEqual(flt(profit["total"]), 100)

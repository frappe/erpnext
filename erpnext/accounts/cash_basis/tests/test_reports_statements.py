# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Profit and Loss, Balance Sheet, Gross and Net Profit on the cash basis (phase 3), with CB-25."""

from unittest.mock import patch

import frappe

from erpnext.accounts import cash_basis
from erpnext.accounts.cash_basis.tests.fixtures import US_COMPANY, acc, set_company_method
from erpnext.accounts.cash_basis.tests.report_case import (
	ReportTestCase,
	comparable,
	report_values,
	row_value,
)
from erpnext.accounts.cash_basis.tests.vouchers import line, make_sales_invoice, pay, save
from erpnext.accounts.report.balance_sheet import balance_sheet
from erpnext.accounts.report.gross_and_net_profit_report import gross_and_net_profit_report
from erpnext.accounts.report.profit_and_loss_statement import profit_and_loss_statement
from erpnext.tests.utils import change_settings

SALES = acc("Sales")
DEBTORS = acc("Debtors")
TAX = acc("ST 6%")
BANK = acc("Test Bank")
RETAINED = acc("Retained Earnings")
PL = profit_and_loss_statement.execute
BS = balance_sheet.execute
GROSS = gross_and_net_profit_report.execute


class TestCashBasisStatements(ReportTestCase):
	def make_cb04(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-04-10", 55)

	def test_i7_accrual_output_is_identical(self):
		self.make_cb04()
		reports = (
			(PL, "2026-01-01", "2026-12-31", {}),
			(BS, "2026-01-01", "2026-12-31", {"accumulated_values": 1}),
			(GROSS, "2026-01-01", "2026-12-31", {"from_fiscal_year": None, "to_fiscal_year": None}),
		)
		set_company_method(US_COMPANY, "Accrual")
		before = [comparable(self.run_report(r, f, t, **x)) for r, f, t, x in reports]
		set_company_method(US_COMPANY, "Cash")
		after = [
			comparable(self.run_report(r, f, t, accounting_method="Accrual", **x)) for r, f, t, x in reports
		]
		self.assertEqual(before, after)
		cash = [comparable(self.run_report(r, f, t, **x)) for r, f, t, x in reports]
		self.assertNotEqual(before, cash, "with the Company default Cash, the reports change")

	def test_profit_and_loss_on_cash_basis(self):
		self.make_cb04()
		accrual = self.run_report(PL, "2026-01-01", "2026-12-31", accounting_method="Accrual")
		cash = self.run_report(PL, "2026-01-01", "2026-12-31")
		self.assertEqual(report_values(accrual, SALES), 100)
		self.assertEqual(report_values(cash, SALES), 50)
		self.assertIn("Accounting Method: Cash", cash[2])
		self.assertIn("Accounting Method: Accrual", accrual[2])

		monthly = self.run_report(PL, "2026-01-01", "2026-12-31", periodicity="Monthly")
		self.assertEqual(report_values(monthly, SALES, "mar_2026"), 0)
		self.assertEqual(report_values(monthly, SALES, "apr_2026"), 50)

	def test_accrual_banner(self):
		# The filter is not set and the Company default is Accrual, or the filter is Accrual.
		set_company_method(US_COMPANY, "Accrual")
		for filters in ({}, {"accounting_method": "Accrual"}):
			for report in (PL, BS, GROSS):
				message = self.run_report(report, "2026-01-01", "2026-12-31", **filters)[2]
				self.assertIn("Accounting Method: Accrual", message)
				self.assertIn('data-theme="blue"', message)
				self.assertIn("#icon-info-solid", message)
				self.assertIn("reported when they are invoiced", message)
				self.assertNotIn("receivables and payables", message)

	def test_no_banner_outside_the_rollout_scope(self):
		# The company cannot choose a method, so the report output stays as before the feature.
		with patch.object(cash_basis, "CASH_METHOD_COUNTRIES", ()):
			for report in (PL, BS, GROSS):
				result = self.run_report(report, "2026-01-01", "2026-12-31")
				self.assertIsNone(result[2] if len(result) > 2 else None)

	def test_balance_sheet_on_cash_basis_balances(self):
		self.make_cb04()
		result = self.run_report(BS, "2026-01-01", "2026-04-30", accumulated_values=1)
		# Section 6.5 example: receivable 5, tax 10, bank 55, profit 50.
		self.assertEqual(report_values(result, DEBTORS), 5)
		self.assertEqual(report_values(result, TAX), 10)
		self.assertEqual(report_values(result, BANK), 55)
		self.assertEqual(row_value(result, "account_name", "Provisional Profit"), 50)
		self.assertNotIn("not closed", result[2] or "")
		self.assertIn("receivables and payables show only the tax of unpaid invoices", result[2])
		# No exceptions: a blue alert.
		self.assertIn('data-theme="blue"', result[2])

	def test_gross_and_net_profit_on_cash_basis(self):
		self.make_cb04()
		result = self.run_report(GROSS, "2026-01-01", "2026-12-31")
		self.assertEqual(report_values(result, SALES), 50)
		self.assertIn("Accounting Method: Cash", result[2])

	def test_snapshot_path_falls_back_with_cash(self):
		self.make_cb04()
		filters = self.report_filters("2026-01-01", "2026-12-31")
		result = profit_and_loss_statement.execute_snapshot_report(filters)
		self.assertEqual(report_values(result, SALES), 50)
		filters = self.report_filters("2026-01-01", "2026-04-30", accumulated_values=1)
		self.assertEqual(report_values(balance_sheet.execute_snapshot_report(filters), DEBTORS), 5)

	def test_company_outside_scope_stays_accrual(self):
		set_company_method(US_COMPANY, "Accrual")
		self.make_cb04()
		frappe.db.set_value("Company", US_COMPANY, "country", "Canada")
		result = self.run_report(PL, "2026-01-01", "2026-12-31", accounting_method="Cash")
		self.assertEqual(report_values(result, SALES), 100)

	def unresolved_income(self, **extra):
		"""Income from the shared get_data, with filters that no report resolved."""
		from erpnext.accounts.report.financial_statements import get_data, get_period_list

		filters = self.report_filters("2026-01-01", "2026-12-31", **extra)
		periods = get_period_list(
			None, None, "2026-01-01", "2026-12-31", "Date Range", "Yearly", company=US_COMPANY
		)
		data = get_data(US_COMPANY, "Income", "Credit", periods, filters=filters, ignore_closing_entries=True)
		return report_values((periods_as_columns(periods), data), SALES, periods[-1]["key"])

	def test_report_that_does_not_resolve_the_method_stays_accrual(self):
		self.make_cb04()
		# Every report in section 9 resolves the method by phase 6. A caller that does not stays accrual.
		self.assertEqual(self.unresolved_income(accounting_method="Cash"), 100)

	def test_client_cannot_mark_a_report_as_converting(self):
		from frappe.desk.query_report import run

		self.make_cb04()
		faked = {"accounting_method": "Cash", "_cash_basis_resolved": 1, "_cash_basis_result": "x"}
		self.assertEqual(self.unresolved_income(**faked), 100)
		# The desk path of a converting report works, and the result can go to JSON.
		pl_filters = self.report_filters("2026-01-01", "2026-12-31", accounting_method="Cash")
		result = run(
			"Profit and Loss Statement", filters=frappe.as_json({**pl_filters, "_cash_basis_resolved": 1})
		)
		self.assertIn("Accounting Method: Cash", result["message"])

	def make_closed_year(self, **line_fields):
		make_sales_invoice("2026-03-01", [line(100, **line_fields)])
		fiscal_year = frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"})
		closing = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": "2026-12-31",
				"period_start_date": "2026-01-01",
				"period_end_date": "2026-12-31",
				"company": US_COMPANY,
				"fiscal_year": fiscal_year,
				"cost_center": acc("Main"),
				"closing_account_head": RETAINED,
				"remarks": "Cash basis test",
			}
		)
		save(closing, submit=True)
		return closing

	@change_settings("Accounts Settings", {"use_legacy_controller_for_pcv": 1})
	def test_closing_transfer_keeps_the_project(self):
		project = frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test Cash Basis Closing", "company": US_COMPANY}
		).insert()
		self.make_closed_year(project=project.name)
		result = self.run_report(BS, "2026-01-01", "2026-12-31", accumulated_values=1, project=[project.name])
		# The accrual PCV closes the profit of the project to Retained Earnings with the project.
		# The cash transfer keeps the project too, so the cash retained earnings are 0.
		self.assertEqual(report_values(result, RETAINED), 0)

	@change_settings("Accounts Settings", {"use_legacy_controller_for_pcv": 1})
	def test_cb25_period_closing_between_invoice_and_payment(self):
		make_sales_invoice("2026-03-01", [line(100)])
		fiscal_year = frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"})
		closing = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": "2026-12-31",
				"period_start_date": "2026-01-01",
				"period_end_date": "2026-12-31",
				"company": US_COMPANY,
				"fiscal_year": fiscal_year,
				"cost_center": acc("Main"),
				"closing_account_head": RETAINED,
				"remarks": "Cash basis test",
			}
		)
		save(closing, submit=True)
		invoice = frappe.get_last_doc("Sales Invoice", {"company": US_COMPANY})
		pay(invoice, "2027-02-10")

		# 2026: no cash. The PCV closes the accrual profit of 100; the cash basis closes 0.
		self.assertEqual(report_values(self.run_report(PL, "2026-01-01", "2026-12-31"), SALES), 0)
		bs_2026 = self.run_report(BS, "2026-01-01", "2026-12-31", accumulated_values=1)
		self.assertEqual(report_values(bs_2026, RETAINED), 0)
		self.assertEqual(report_values(bs_2026, DEBTORS), 0)

		# 2027: the payment is income. The opening from the closing balances stays in balance.
		self.assertEqual(report_values(self.run_report(PL, "2027-01-01", "2027-12-31"), SALES), 100)
		accrual_2027 = self.run_report(
			BS, "2027-01-01", "2027-12-31", accumulated_values=1, accounting_method="Accrual"
		)
		cash_2027 = self.run_report(BS, "2027-01-01", "2027-12-31", accumulated_values=1)
		self.assertEqual(report_values(accrual_2027, RETAINED), 100)
		self.assertEqual(report_values(cash_2027, RETAINED), 0)
		self.assertEqual(row_value(cash_2027, "account_name", "Provisional Profit"), 100)
		self.assertEqual(report_values(cash_2027, BANK), 100)
		self.assertNotIn("not closed", cash_2027[2] or "")

		with change_settings("Accounts Settings", {"ignore_account_closing_balance": 1}):
			from_ledger = self.run_report(BS, "2027-01-01", "2027-12-31", accumulated_values=1)
		self.assertEqual(comparable(from_ledger), comparable(cash_2027))
		self.assert_invariants("2027-12-31")
		self.assert_invariants("2026-12-31", from_date="2026-01-01")


def periods_as_columns(periods):
	return [{"fieldname": period["key"]} for period in periods]

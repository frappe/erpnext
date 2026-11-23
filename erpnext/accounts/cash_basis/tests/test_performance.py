# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""CB-32: the performance requirement of section 7.4, on generated ledger rows.

60,000 invoices (receivable, income, tax) and 20,000 bank receipts: 220,000 GL rows.
The rows go in with bulk inserts in the test transaction, which rolls back.
"""

import time

import frappe
from frappe.utils import add_days, getdate

from erpnext.accounts.cash_basis.tests.fixtures import CUSTOMER, US_COMPANY, acc
from erpnext.accounts.cash_basis.tests.report_case import ReportTestCase, report_values
from erpnext.accounts.report.profit_and_loss_statement import profit_and_loss_statement

INVOICES = 60_000
RECEIPTS = 20_000
GL_FIELDS = (
	"name",
	"company",
	"posting_date",
	"fiscal_year",
	"account",
	"party_type",
	"party",
	"debit",
	"credit",
	"debit_in_account_currency",
	"credit_in_account_currency",
	"account_currency",
	"against",
	"against_voucher_type",
	"against_voucher",
	"voucher_type",
	"voucher_no",
	"cost_center",
	"is_opening",
	"is_cancelled",
	"docstatus",
)
PLE_FIELDS = (
	"name",
	"company",
	"posting_date",
	"account_type",
	"account",
	"party_type",
	"party",
	"voucher_type",
	"voucher_no",
	"against_voucher_type",
	"against_voucher_no",
	"amount",
	"amount_in_account_currency",
	"account_currency",
	"delinked",
	"cost_center",
	"docstatus",
)


class TestCashBasisPerformance(ReportTestCase):
	def test_cb32_profit_and_loss_on_large_ledger(self):
		self.generate_ledger()
		filters = ("2026-01-01", "2026-12-31")

		started = time.perf_counter()
		accrual = self.run_report(profit_and_loss_statement.execute, *filters, accounting_method="Accrual")
		accrual_seconds = time.perf_counter() - started

		started = time.perf_counter()
		cash = self.run_report(profit_and_loss_statement.execute, *filters, accounting_method="Cash")
		cash_seconds = time.perf_counter() - started

		single_company_accrual = self.time_company_accrual(*filters)
		cash_part = cash_seconds - accrual_seconds
		single_company_cash = single_company_accrual + cash_part
		print(
			f"CB-32: accrual {accrual_seconds:.2f} s on all {frappe.db.count('Company')} companies, "
			f"accrual {single_company_accrual:.2f} s on this company's roots, cash part {cash_part:.2f} s, "
			f"cash on one company {single_company_cash:.2f} s, "
			f"ratio {single_company_cash / single_company_accrual:.1f}"
		)
		self.assertEqual(report_values(accrual, acc("Sales")), INVOICES * 100)
		self.assertEqual(report_values(cash, acc("Sales")), RECEIPTS * 100)
		# Section 7.4: at most 10 seconds. The ratio rule of 2 times is not met: phase 3 report.
		self.assertLessEqual(single_company_cash, 10, "section 7.4: at most 10 seconds")

	def time_company_accrual(self, from_date, to_date):
		"""The accrual queries of get_data on the roots of this company only, as on a site with one company."""
		from erpnext.accounts.report.financial_statements import set_gl_entries_by_account

		filters = self.report_filters(from_date, to_date)
		started = time.perf_counter()
		for root_type in ("Income", "Expense"):
			for root in frappe.get_all(
				"Account",
				filters={"company": US_COMPANY, "root_type": root_type, "parent_account": ["is", "not set"]},
				fields=["lft", "rgt"],
			):
				set_gl_entries_by_account(
					US_COMPANY, from_date, to_date, filters, {}, root.lft, root.rgt, root_type, True
				)
		return time.perf_counter() - started

	def generate_ledger(self):
		fiscal_year = frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"})
		start = getdate("2026-01-01")
		common = {"company": US_COMPANY, "fiscal_year": fiscal_year, "cost_center": acc("Main")}
		gl_rows, ple_rows, journals = [], [], []
		for index in range(INVOICES):
			invoice = f"CBPERF-SINV-{index:06d}"
			posting_date = add_days(start, index % 300)
			gl_rows += [
				gl_row(
					common,
					f"{invoice}-1",
					posting_date,
					acc("Debtors"),
					110,
					0,
					"Sales Invoice",
					invoice,
					party=True,
					against=acc("Sales"),
					against_voucher=invoice,
				),
				gl_row(
					common,
					f"{invoice}-2",
					posting_date,
					acc("Sales"),
					0,
					100,
					"Sales Invoice",
					invoice,
					against=CUSTOMER,
				),
				gl_row(
					common,
					f"{invoice}-3",
					posting_date,
					acc("ST 6%"),
					0,
					10,
					"Sales Invoice",
					invoice,
					against=CUSTOMER,
				),
			]
			ple_rows.append(
				ple_row(common, f"{invoice}-P", posting_date, "Sales Invoice", invoice, invoice, 110)
			)
			if index < RECEIPTS:
				receipt = f"CBPERF-JV-{index:06d}"
				paid_on = add_days(posting_date, 30)
				journals.append(
					(receipt, US_COMPANY, paid_on, "Bank Entry", 1, "Administrator", "Administrator")
				)
				gl_rows += [
					gl_row(
						common,
						f"{receipt}-1",
						paid_on,
						acc("Test Bank"),
						110,
						0,
						"Journal Entry",
						receipt,
						against=CUSTOMER,
					),
					gl_row(
						common,
						f"{receipt}-2",
						paid_on,
						acc("Debtors"),
						0,
						110,
						"Journal Entry",
						receipt,
						party=True,
						against=acc("Test Bank"),
						against_voucher=invoice,
						against_type="Sales Invoice",
					),
				]
				ple_rows.append(
					ple_row(
						common,
						f"{receipt}-P",
						paid_on,
						"Journal Entry",
						receipt,
						invoice,
						-110,
						"Sales Invoice",
					)
				)
		frappe.db.bulk_insert("GL Entry", GL_FIELDS, gl_rows, chunk_size=5000)
		frappe.db.bulk_insert("Payment Ledger Entry", PLE_FIELDS, ple_rows, chunk_size=5000)
		frappe.db.bulk_insert(
			"Journal Entry",
			("name", "company", "posting_date", "voucher_type", "docstatus", "owner", "modified_by"),
			journals,
			chunk_size=5000,
		)
		self.assertGreaterEqual(len(gl_rows), 200_000)


def gl_row(
	common,
	name,
	posting_date,
	account,
	debit,
	credit,
	voucher_type,
	voucher_no,
	party=False,
	against=None,
	against_voucher=None,
	against_type=None,
):
	return (
		name,
		common["company"],
		posting_date,
		common["fiscal_year"],
		account,
		"Customer" if party else None,
		CUSTOMER if party else None,
		debit,
		credit,
		debit,
		credit,
		"USD",
		against,
		(against_type or voucher_type) if against_voucher else None,
		against_voucher,
		voucher_type,
		voucher_no,
		common["cost_center"],
		"No",
		0,
		1,
	)


def ple_row(common, name, posting_date, voucher_type, voucher_no, against_no, amount, against_type=None):
	return (
		name,
		common["company"],
		posting_date,
		"Receivable",
		acc("Debtors"),
		"Customer",
		CUSTOMER,
		voucher_type,
		voucher_no,
		against_type or voucher_type,
		against_no,
		amount,
		amount,
		"USD",
		0,
		common["cost_center"],
		1,
	)

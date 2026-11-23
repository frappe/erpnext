# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""CB-26 (filters), CB-27 (presentation currency), CB-31 (user permissions) on the cash basis."""

import frappe

from erpnext.accounts.cash_basis.tests.fixtures import CUSTOMER, US_COMPANY, acc
from erpnext.accounts.cash_basis.tests.report_case import ReportTestCase, report_values
from erpnext.accounts.cash_basis.tests.vouchers import (
	line,
	make_advance,
	make_journal_entry,
	make_sales_invoice,
	pay,
)
from erpnext.accounts.report.general_and_payment_ledger_comparison import (
	general_and_payment_ledger_comparison,
)
from erpnext.accounts.report.profit_and_loss_statement import profit_and_loss_statement

SALES = acc("Sales")
SERVICE = acc("Service")
DEBTORS = acc("Debtors")
MAIN, SECOND = acc("Main"), acc("Second")
PL = profit_and_loss_statement.execute
YEAR = ("2026-01-01", "2026-12-31")


class TestCashBasisReportFilters(ReportTestCase):
	def make_two_line_invoice(self, **sales_line):
		invoice = make_sales_invoice(
			"2026-03-01",
			[
				line(60, account=SALES, cost_center=MAIN, **sales_line),
				line(40, account=SERVICE, cost_center=SECOND),
			],
		)
		pay(invoice, "2026-04-10", 50)
		return invoice

	def profit_and_loss(self, **filters):
		return {
			method: self.run_report(PL, *YEAR, accounting_method=method, **filters)
			for method in ("Accrual", "Cash")
		}

	def assert_values(self, results, account, accrual, cash):
		self.assertEqual(report_values(results["Accrual"], account), accrual, f"Accrual {account}")
		self.assertEqual(report_values(results["Cash"], account), cash, f"Cash {account}")

	def test_cb26_cost_center_filter(self):
		self.make_two_line_invoice()
		results = self.profit_and_loss(cost_center=[SECOND])
		self.assert_values(results, SERVICE, 40, 20)
		self.assert_values(results, SALES, 0, 0)

	def test_cb26_project_filter(self):
		project = frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test Cash Basis Project", "company": US_COMPANY}
		).insert()
		self.make_two_line_invoice(project=project.name)
		results = self.profit_and_loss(project=[project.name])
		self.assert_values(results, SALES, 60, 30)
		self.assert_values(results, SERVICE, 0, 0)

	def test_cb26_dimension_filter(self):
		department = frappe.get_doc(
			{"doctype": "Department", "department_name": "_Test Cash Basis Department", "company": US_COMPANY}
		).insert()
		self.make_two_line_invoice(department=department.name)
		results = self.profit_and_loss(department=[department.name])
		self.assert_values(results, SALES, 60, 30)
		self.assert_values(results, SERVICE, 0, 0)

	def test_cb26_finance_book_filter(self):
		book = frappe.get_doc(
			{"doctype": "Finance Book", "finance_book_name": "_Test Cash Basis Book"}
		).insert()
		journal = make_journal_entry(
			"2026-03-01",
			[
				{"account": DEBTORS, "debit": 100, "party_type": "Customer", "party": CUSTOMER},
				{"account": SERVICE, "credit": 100},
			],
			finance_book=book.name,
		)
		make_advance(
			"Customer", CUSTOMER, "2026-04-10", 100, references=[("Journal Entry", journal.name, 100)]
		)
		# Without the book, the rows of the book are out, for both methods.
		self.assert_values(self.profit_and_loss(), SERVICE, 0, 0)
		# With the book, the recognition rows carry the book of the line.
		self.assert_values(self.profit_and_loss(finance_book=book.name), SERVICE, 100, 100)

	def test_cb27_presentation_currency(self):
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
		self.make_two_line_invoice()
		results = self.profit_and_loss(presentation_currency="EUR")
		self.assert_values(results, SALES, 30, 15)
		self.assert_values(results, SERVICE, 20, 10)

	def test_cb31_user_with_permission_limits(self):
		self.make_two_line_invoice()
		user = "test-cash-basis-accountant@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Cash Basis Accountant",
					"roles": [{"role": "Accounts User"}, {"role": "Accounts Manager"}],
				}
			).insert()
		for allow, value in (("Company", US_COMPANY), ("Cost Center", MAIN)):
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
			results = self.profit_and_loss()
		# The user sees the line of the cost center Main only. The calculation still reads
		# the whole invoice, so the ratio is the same as for a user with no limit.
		self.assert_values(results, SALES, 60, 30)
		self.assert_values(results, SERVICE, 0, 0)

	def test_payment_ledger_matches_general_ledger(self):
		"""Section 18, phase 3 fact: the comparison report finds no difference on these vouchers."""
		self.make_two_line_invoice()
		filters = frappe._dict(
			company=US_COMPANY, period_start_date="2026-01-01", period_end_date="2026-12-31"
		)
		columns, data = general_and_payment_ledger_comparison.execute(filters)
		self.assertEqual(data, [])

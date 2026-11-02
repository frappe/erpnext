# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.profitability_analysis.profitability_analysis import execute

INCOME = "Sales - _TC"
EXPENSE = "_Test Account Cost for Goods Sold - _TC"
BANK = "_Test Bank - _TC"


class TestProfitabilityAnalysis(FrappeTestCase):
	def setUp(self):
		for year in (2025, 2026):
			fiscal_year = f"_Test Fiscal Year {year}"
			if not frappe.db.exists("Fiscal Year", fiscal_year):
				frappe.get_doc(
					{
						"doctype": "Fiscal Year",
						"year": fiscal_year,
						"year_start_date": f"{year}-01-01",
						"year_end_date": f"{year}-12-31",
						"companies": [{"company": "_Test Company"}],
					}
				).insert(ignore_if_duplicate=True)

	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, fiscal_year="_Test Fiscal Year 2026", **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"based_on": "Cost Center",
				"fiscal_year": fiscal_year,
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				**extra,
			}
		)
		return execute(filters)[1]

	def make_cc(self, name, **args):
		create_cost_center(cost_center_name=name, **args)
		return name + " - _TC"

	def row(self, data, account):
		return next(r for r in data if r.get("account") == account)

	def book_income(self, cost_center, amount, posting_date="2026-06-01"):
		create_sales_invoice(
			cost_center=cost_center, income_account=INCOME, rate=amount, qty=1, posting_date=posting_date
		)

	def book_expense(self, cost_center, amount, posting_date="2026-06-01"):
		make_journal_entry(
			EXPENSE, BANK, amount, cost_center=cost_center, posting_date=posting_date, submit=True
		)

	def test_income_expense_and_gross_profit(self):
		# a dedicated leaf cost center keeps these exact assertions free of GL that
		# other tests may book against a shared cost center in the same fiscal year
		cc = self.make_cc("_Test PA Income Expense")
		self.book_income(cc, 10000)
		self.book_expense(cc, 4000)

		row = self.row(self.run_report(), cc)
		self.assertEqual(row["income"], 10000)
		self.assertEqual(row["expense"], 4000)
		self.assertEqual(row["gross_profit_loss"], 6000)

	def test_parent_cost_center_accumulates_children(self):
		parent = self.make_cc("_Test PA Parent", is_group=1)
		child_1 = self.make_cc("_Test PA Child 1", parent_cost_center=parent)
		child_2 = self.make_cc("_Test PA Child 2", parent_cost_center=parent)

		self.book_income(child_1, 10000)
		self.book_expense(child_2, 3000)

		data = self.run_report()
		self.assertEqual(self.row(data, child_1)["income"], 10000)
		self.assertEqual(self.row(data, child_2)["expense"], 3000)

		parent_row = self.row(data, parent)
		self.assertEqual(parent_row["income"], 10000)
		self.assertEqual(parent_row["expense"], 3000)
		self.assertEqual(parent_row["gross_profit_loss"], 7000)

	def test_date_range_excludes_out_of_period_entries(self):
		cc = self.make_cc("_Test PA Date Range")
		self.book_income(cc, 10000, posting_date="2025-06-01")

		# the 2025 income must not appear in a 2026 report (zero-value rows are dropped)
		accounts_2026 = {r.get("account") for r in self.run_report()}
		self.assertNotIn(cc, accounts_2026)

		row_2025 = self.row(
			self.run_report(
				fiscal_year="_Test Fiscal Year 2025", from_date="2025-01-01", to_date="2025-12-31"
			),
			cc,
		)
		self.assertEqual(row_2025["income"], 10000)

	def test_total_row_sums_income_and_expense(self):
		cc = "_Test Cost Center - _TC"
		self.book_income(cc, 10000)
		self.book_expense(cc, 4000)

		data = self.run_report()
		# the report appends a blank separator row and a totals row at the end
		total_row = data[-1]
		# the report wraps the (possibly translated) "Total" label in single quotes
		self.assertEqual(total_row["account"], "'" + frappe._("Total") + "'")
		# total is built from direct (non-accumulated) values, so it stays internally consistent
		self.assertEqual(total_row["gross_profit_loss"], total_row["income"] - total_row["expense"])
		# and it includes this test's bookings
		self.assertGreaterEqual(total_row["income"], 10000)
		self.assertGreaterEqual(total_row["expense"], 4000)

	def test_restricted_user_sees_only_permitted_cost_center_figures(self):
		permitted = self.make_cc("_Test PA Permitted")
		restricted = self.make_cc("_Test PA Restricted")
		self.book_income(permitted, 400)
		self.book_income(restricted, 1000)
		user = make_restricted_user("test_profitability_analysis@example.com", "Cost Center", permitted)

		frappe.set_user(user)
		try:
			data = self.run_report(show_zero_values=1)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(data[-1]["income"], 400)
		cost_centers = {row.get("account") for row in data}
		self.assertIn(permitted, cost_centers)
		self.assertNotIn(restricted, cost_centers)

	def test_restricted_user_sees_only_permitted_projects(self):
		permitted, restricted = (
			frappe.get_doc({"doctype": "Project", "project_name": name, "company": "_Test Company"})
			.insert()
			.name
			for name in ("_Test PA Permitted Project", "_Test PA Restricted Project")
		)
		user = make_restricted_user(
			"test_profitability_analysis_project@example.com",
			"Project",
			permitted,
			roles=["Accounts User", "Projects User"],
		)

		frappe.set_user(user)
		try:
			data = self.run_report(based_on="Project", show_zero_values=1)
		finally:
			frappe.set_user("Administrator")

		projects = {row.get("account") for row in data}
		self.assertIn(permitted, projects)
		self.assertNotIn(restricted, projects)

	def test_user_without_company_permission_cannot_run_report_on_accounting_dimension(self):
		user = make_restricted_user(
			"test_profitability_analysis_company@example.com", "Company", "_Test Company 1"
		)

		frappe.set_user(user)
		try:
			self.assertRaises(
				frappe.PermissionError,
				self.run_report,
				based_on="Accounting Dimension",
				accounting_dimension="Location",
			)
		finally:
			frappe.set_user("Administrator")

	def test_entries_of_other_finance_books_are_left_out(self):
		cc = self.make_cc("_Test PA Finance Book")
		self.book_expense(cc, 300)
		journal_entry = make_journal_entry(
			EXPENSE, BANK, 500, cost_center=cc, posting_date="2026-06-01", save=False
		)
		journal_entry.finance_book = (
			frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "_Test PA Finance Book"})
			.insert(ignore_if_duplicate=True)
			.name
		)
		journal_entry.submit()

		self.assertEqual(self.row(self.run_report(), cc)["expense"], 300)
		data = self.run_report(finance_book=journal_entry.finance_book)
		self.assertEqual(self.row(data, cc)["expense"], 800)


def make_restricted_user(user, doctype, value, roles=("Accounts User",)):
	if not frappe.db.exists("User", user):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user,
				"first_name": "Profitability Analysis",
				"roles": [{"role": role} for role in roles],
			}
		).insert()
	frappe.permissions.add_user_permission(doctype, value, user)
	return user

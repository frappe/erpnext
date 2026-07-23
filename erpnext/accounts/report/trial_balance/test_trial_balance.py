# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.report.trial_balance.trial_balance import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestTrialBalance(ERPNextTestSuite):
	def setUp(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.utils import get_fiscal_year

		create_cost_center(
			cost_center_name="Test Cost Center",
			company="Trial Balance Company",
			parent_cost_center="Trial Balance Company - TBC",
		)
		create_account(
			account_name="Offsetting",
			company="Trial Balance Company",
			parent_account="Temporary Accounts - TBC",
		)
		self.fiscal_year = get_fiscal_year(today(), company="Trial Balance Company")[0]
		dim = frappe.get_doc("Accounting Dimension", "Branch")
		dim.append(
			"dimension_defaults",
			{
				"company": "Trial Balance Company",
				"automatically_post_balancing_accounting_entry": 1,
				"offsetting_account": "Offsetting - TBC",
			},
		)
		dim.save()

	def test_offsetting_entries_for_accounting_dimensions(self):
		"""
		Checks if Trial Balance Report is balanced when filtered using a particular Accounting Dimension
		"""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		branch1 = frappe.new_doc("Branch")
		branch1.branch = "Location 1"
		branch1.insert(ignore_if_duplicate=True)
		branch2 = frappe.new_doc("Branch")
		branch2.branch = "Location 2"
		branch2.insert(ignore_if_duplicate=True)

		si = create_sales_invoice(
			company="Trial Balance Company",
			debit_to="Debtors - TBC",
			cost_center="Test Cost Center - TBC",
			income_account="Sales - TBC",
			do_not_submit=1,
		)
		si.branch = "Location 1"
		si.items[0].branch = "Location 2"
		si.save()
		si.submit()

		filters = frappe._dict(
			{"company": "Trial Balance Company", "fiscal_year": self.fiscal_year, "branch": ["Location 1"]}
		)
		total_row = execute(filters)[1][-1]
		self.assertEqual(total_row["debit"], total_row["credit"])


class TestTrialBalanceReport(ERPNextTestSuite):
	"""Correctness tests using fresh accounts so the asserted rows are unpolluted."""

	def make_accounts_and_entry(self, amount, posting_date):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		debit_account = create_account(
			account_name="_Test Trial Balance Debit",
			company="_Test Company",
			parent_account="Current Assets - _TC",
		)
		credit_account = create_account(
			account_name="_Test Trial Balance Credit",
			company="_Test Company",
			parent_account="Current Assets - _TC",
		)
		make_journal_entry(debit_account, credit_account, amount, posting_date=posting_date, submit=True)
		return debit_account, credit_account

	def rows_by_account(self, **filters):
		from erpnext.accounts.utils import get_fiscal_year

		filters.setdefault("company", "_Test Company")
		filters.setdefault("fiscal_year", get_fiscal_year(today(), company="_Test Company")[0])
		data = execute(frappe._dict(filters))[1]
		return {row["account"]: row for row in data if row.get("account")}, data[-1]

	def test_posted_entry_lands_in_period_and_total_balances(self):
		debit_account, credit_account = self.make_accounts_and_entry(500, today())

		rows, total_row = self.rows_by_account()

		self.assertEqual(rows[debit_account]["debit"], 500)
		self.assertEqual(rows[credit_account]["credit"], 500)
		self.assertEqual(total_row["debit"], total_row["credit"])

	def test_entry_before_from_date_shows_as_opening_balance(self):
		from erpnext.accounts.utils import get_fiscal_year

		fiscal_year, year_start, year_end = get_fiscal_year(today(), company="_Test Company")
		debit_account, credit_account = self.make_accounts_and_entry(500, year_start)

		rows, _ = self.rows_by_account(
			fiscal_year=fiscal_year, from_date=add_days(year_start, 5), to_date=year_end
		)

		# the entry predates the period, so it belongs in opening - not in the period columns
		self.assertEqual(rows[debit_account]["opening_debit"], 500)
		self.assertEqual(rows[debit_account]["debit"], 0)
		self.assertEqual(rows[credit_account]["opening_credit"], 500)

	def test_show_zero_values_includes_unposted_accounts(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		account = create_account(
			account_name="_Test Trial Balance Zero",
			company="_Test Company",
			parent_account="Current Assets - _TC",
		)

		# an account with no postings is hidden by default, shown when the filter is on
		self.assertNotIn(account, self.rows_by_account()[0])
		self.assertIn(account, self.rows_by_account(show_zero_values=1)[0])

	def test_show_group_accounts_includes_parent_rows(self):
		self.make_accounts_and_entry(500, today())

		# group (parent) accounts are hidden by default, shown when the filter is on
		self.assertNotIn("Current Assets - _TC", self.rows_by_account()[0])
		self.assertIn("Current Assets - _TC", self.rows_by_account(show_group_accounts=1)[0])

	def test_show_net_values_nets_opening_and_closing(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
		from erpnext.accounts.utils import get_fiscal_year

		fiscal_year, year_start, year_end = get_fiscal_year(today(), company="_Test Company")
		account = create_account(
			account_name="_Test Trial Balance Net",
			company="_Test Company",
			parent_account="Current Assets - _TC",
		)
		offset = create_account(
			account_name="_Test Trial Balance Net Offset",
			company="_Test Company",
			parent_account="Current Assets - _TC",
		)
		# opening debit 500 (before the period), then a 300 credit within the period
		make_journal_entry(account, offset, 500, posting_date=year_start, submit=True)
		make_journal_entry(offset, account, 300, posting_date=today(), submit=True)

		period = dict(fiscal_year=fiscal_year, from_date=add_days(year_start, 5), to_date=year_end)

		gross = self.rows_by_account(**period)[0][account]
		self.assertEqual(gross["closing_debit"], 500)
		self.assertEqual(gross["closing_credit"], 300)

		net = self.rows_by_account(show_net_values=1, **period)[0][account]
		self.assertEqual(net["closing_debit"], 200)  # 500 debit - 300 credit
		self.assertEqual(net["closing_credit"], 0)

	def test_opening_balance_respects_ignore_account_closing_balance(self):
		"""With a Period Closing Voucher present, opening can be read from the cached
		Account Closing Balance or recomputed from GL; both must agree."""
		self.close_fiscal_year_2021_for_pcv_company()

		def cash_opening(ignore_closing_balance):
			frappe.db.set_single_value(
				"Accounts Settings", "ignore_account_closing_balance", ignore_closing_balance
			)
			data = execute(frappe._dict(company="Test PCV Company", fiscal_year="_Test Fiscal Year 2022"))[1]
			return next(row["opening_debit"] for row in data if row.get("account") == "Cash - TPC")

		from_cache = cash_opening(0)  # reads the Account Closing Balance
		from_gl = cash_opening(1)  # recomputes from GL Entry

		self.assertEqual(from_cache, 400)
		self.assertEqual(from_gl, 400)
		self.assertEqual(from_cache, from_gl)

	def test_period_closing_entry_filter_includes_closing_entries(self):
		surplus = self.close_fiscal_year_2021_for_pcv_company()

		def surplus_period_credit(include_closing):
			data = execute(
				frappe._dict(
					company="Test PCV Company",
					fiscal_year="_Test Fiscal Year 2021",
					with_period_closing_entry_for_current_period=include_closing,
				)
			)[1]
			row = next((row for row in data if row.get("account") == surplus), None)
			return row["credit"] if row else 0

		# the closing entry posts to the surplus account only when the filter is on
		self.assertEqual(surplus_period_credit(0), 0)
		self.assertEqual(surplus_period_credit(1), 400)

	def test_show_unclosed_fy_pl_balances_controls_pl_opening(self):
		"""P&L opening from a prior, unclosed fiscal year is excluded by default and
		included only when 'show unclosed FY P&L balances' is on."""
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
		from erpnext.accounts.doctype.period_closing_voucher.test_period_closing_voucher import (
			create_cost_center,
		)

		cost_center = create_cost_center("TB Unclosed CC")
		jv = make_journal_entry(
			"Cost of Goods Sold - TPC",
			"Cash - TPC",
			250,
			cost_center=cost_center,
			posting_date="2020-06-15",
			save=False,
		)
		jv.company = "Test PCV Company"
		jv.save()
		jv.submit()

		def cogs_opening(show_unclosed):
			data = execute(
				frappe._dict(
					company="Test PCV Company",
					fiscal_year="_Test Fiscal Year 2021",
					show_unclosed_fy_pl_balances=show_unclosed,
				)
			)[1]
			row = next((row for row in data if row.get("account") == "Cost of Goods Sold - TPC"), None)
			return row["opening_debit"] if row else 0

		self.assertEqual(cogs_opening(0), 0)  # prior-year P&L excluded by default
		self.assertEqual(cogs_opening(1), 250)  # included when showing unclosed FY P&L

	def test_include_default_book_entries_controls_default_fb_opening(self):
		"""An opening entry tagged with the company's default finance book is included in
		opening only when 'Include Default FB Entries' is on."""
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
		from erpnext.accounts.utils import get_fiscal_year

		finance_book = (
			frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "_Test TB Finance Book"})
			.insert(ignore_if_duplicate=True)
			.name
		)
		frappe.db.set_value("Company", "_Test Company", "default_finance_book", finance_book)

		fiscal_year, year_start, year_end = get_fiscal_year(today(), company="_Test Company")
		account = create_account(
			account_name="_Test Trial Balance FB",
			company="_Test Company",
			parent_account="Current Assets - _TC",
		)
		offset = create_account(
			account_name="_Test Trial Balance FB Offset",
			company="_Test Company",
			parent_account="Current Assets - _TC",
		)
		jv = make_journal_entry(account, offset, 500, posting_date=year_start, save=False)
		jv.finance_book = finance_book
		jv.save()
		jv.submit()

		period = dict(fiscal_year=fiscal_year, from_date=add_days(year_start, 5), to_date=year_end)

		with_default = self.rows_by_account(include_default_book_entries=1, **period)[0]
		self.assertEqual(with_default[account]["opening_debit"], 500)

		without_default = self.rows_by_account(include_default_book_entries=0, **period)[0]
		self.assertEqual(without_default.get(account, {}).get("opening_debit", 0), 0)

	def close_fiscal_year_2021_for_pcv_company(self):
		"""Post a 400 balance to Cash - TPC in FY 2021 and close it with a PCV. Returns the surplus account."""
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
		from erpnext.accounts.doctype.period_closing_voucher.test_period_closing_voucher import (
			create_account,
			create_cost_center,
		)

		frappe.db.set_single_value("Accounts Settings", "use_legacy_controller_for_pcv", 1)
		cost_center = create_cost_center("TB Opening CC")

		jv = make_journal_entry(
			"Cash - TPC", "Sales - TPC", 400, cost_center=cost_center, posting_date="2021-06-15", save=False
		)
		jv.company = "Test PCV Company"
		jv.save()
		jv.submit()

		surplus = create_account()
		pcv = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": "2021-12-31",
				"period_start_date": "2021-01-01",
				"period_end_date": "2021-12-31",
				"company": "Test PCV Company",
				"fiscal_year": "_Test Fiscal Year 2021",
				"cost_center": cost_center,
				"closing_account_head": surplus,
				"remarks": "test",
			}
		)
		pcv.insert()
		pcv.submit()
		return surplus

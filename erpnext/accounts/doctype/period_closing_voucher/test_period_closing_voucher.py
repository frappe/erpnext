# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import flt, formatdate, getdate, today

from erpnext.accounts.doctype.finance_book.test_finance_book import create_finance_book
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.period_closing_voucher.period_closing_voucher import (
	get_period_start_end_date,
	process_gl_and_closing_entries,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.accounts.utils import get_fiscal_year


class TestPeriodClosingVoucher(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("Accounts Settings", "use_legacy_controller_for_pcv", 1)
		create_company()
		for doctype in ("GL Entry", "Period Closing Voucher"):
			table = frappe.qb.DocType(doctype)
			frappe.qb.from_(table).delete().where(table.company == "Test PCV Company").run()

	def tearDown(self):
		frappe.db.rollback()

	def test_closing_entry(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")

		company = create_company()
		cost_center = create_cost_center("Test Cost Center 1")

		jv1 = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center,
			company=company,
			save=False,
		)
		jv1.company = company
		jv1.save()
		jv1.submit()

		jv2 = make_journal_entry(
			posting_date="2021-03-15",
			amount=600,
			account1="Cost of Goods Sold - TPC",
			account2="Cash - TPC",
			cost_center=cost_center,
			company=company,
			save=False,
		)
		jv2.company = company
		jv2.save()
		jv2.submit()

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31")
		surplus_account = pcv.closing_account_head

		expected_gle = (
			("Cost of Goods Sold - TPC", 0.0, 600.0),
			(surplus_account, 200.0, 0.0),
			("Sales - TPC", 400.0, 0.0),
		)

		pcv_gle = frappe.db.sql(
			"""
			select account, debit, credit from `tabGL Entry` where voucher_no=%s order by account
		""",
			(pcv.name),
		)
		pcv.reload()
		self.assertEqual(pcv.gle_processing_status, "Completed")
		self.assertEqual(pcv_gle, expected_gle)

	def test_cost_center_wise_posting(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")

		company = create_company()
		surplus_account = create_account()

		cost_center1 = create_cost_center("Main")
		cost_center2 = create_cost_center("Western Branch")

		create_sales_invoice(
			company=company,
			cost_center=cost_center1,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			rate=400,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
			posting_date="2021-03-15",
		)
		create_sales_invoice(
			company=company,
			cost_center=cost_center2,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			rate=200,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
			posting_date="2021-03-15",
		)

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31", submit=False)
		pcv.save()
		pcv.submit()
		surplus_account = pcv.closing_account_head

		expected_gle = (
			(surplus_account, 0.0, 400.0, cost_center1),
			(surplus_account, 0.0, 200.0, cost_center2),
			("Sales - TPC", 400.0, 0.0, cost_center1),
			("Sales - TPC", 200.0, 0.0, cost_center2),
		)

		pcv_gle = frappe.db.sql(
			"""
			select account, debit, credit, cost_center
			from `tabGL Entry` where voucher_no=%s
			order by account, cost_center
		""",
			(pcv.name),
		)

		self.assertSequenceEqual(pcv_gle, expected_gle)

		pcv.reload()
		pcv.cancel()

		self.assertFalse(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_type": "Period Closing Voucher", "voucher_no": pcv.name, "is_cancelled": 0},
			)
		)

	def test_period_closing_with_finance_book_entries(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")

		company = create_company()
		surplus_account = create_account()
		cost_center = create_cost_center("Test Cost Center 1")

		create_sales_invoice(
			company=company,
			income_account="Sales - TPC",
			expense_account="Cost of Goods Sold - TPC",
			cost_center=cost_center,
			rate=400,
			debit_to="Debtors - TPC",
			currency="USD",
			customer="_Test Customer USD",
			posting_date="2021-03-15",
		)

		jv = make_journal_entry(
			account1="Cash - TPC",
			account2="Sales - TPC",
			amount=400,
			cost_center=cost_center,
			posting_date="2021-03-15",
			company=company,
		)
		jv.company = company
		jv.finance_book = create_finance_book().name
		jv.save()
		jv.submit()

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31")
		surplus_account = pcv.closing_account_head

		expected_gle = (
			(surplus_account, 0.0, 400.0, None),
			(surplus_account, 0.0, 400.0, jv.finance_book),
			("Sales - TPC", 400.0, 0.0, None),
			("Sales - TPC", 400.0, 0.0, jv.finance_book),
		)

		pcv_gle = frappe.db.sql(
			"""
			select account, debit, credit, finance_book
			from `tabGL Entry` where voucher_no=%s
			order by account, finance_book
		""",
			(pcv.name),
		)

		self.assertSequenceEqual(pcv_gle, expected_gle)

	def test_gl_entries_restrictions(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")

		company = create_company()
		cost_center = create_cost_center("Test Cost Center 1")

		self.make_period_closing_voucher(posting_date="2021-03-31")

		jv1 = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center,
			company=company,
			save=False,
		)
		jv1.company = company
		jv1.save()

		self.assertRaises(frappe.ValidationError, jv1.submit)

	def test_closing_balance_with_dimensions_and_test_reposting_entry(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabAccount Closing Balance` where company='Test PCV Company'")

		company = create_company()
		cost_center1 = create_cost_center("Test Cost Center 1")
		cost_center2 = create_cost_center("Test Cost Center 2")

		jv1 = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center1,
			company=company,
			save=False,
		)
		jv1.company = company
		jv1.save()
		jv1.submit()

		jv2 = make_journal_entry(
			posting_date="2021-03-15",
			amount=200,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center2,
			company=company,
			save=False,
		)
		jv2.company = company
		jv2.save()
		jv2.submit()

		pcv1 = self.make_period_closing_voucher(posting_date="2021-03-31")

		closing_balance = frappe.db.get_value(
			"Account Closing Balance",
			{
				"account": "Sales - TPC",
				"cost_center": cost_center1,
				"period_closing_voucher": pcv1.name,
				"is_period_closing_voucher_entry": 0,
			},
			["credit", "credit_in_account_currency"],
			as_dict=1,
		)

		self.assertEqual(closing_balance.credit, 400)
		self.assertEqual(closing_balance.credit_in_account_currency, 400)

		jv3 = make_journal_entry(
			posting_date="2022-03-15",
			amount=300,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center2,
			company=company,
			save=False,
		)

		jv3.company = company
		jv3.save()
		jv3.submit()

		pcv2 = self.make_period_closing_voucher(posting_date="2022-03-31")

		cc1_closing_balance = frappe.db.get_value(
			"Account Closing Balance",
			{
				"account": "Sales - TPC",
				"cost_center": cost_center1,
				"period_closing_voucher": pcv2.name,
				"is_period_closing_voucher_entry": 0,
			},
			["credit", "credit_in_account_currency"],
			as_dict=1,
		)

		cc2_closing_balance = frappe.db.get_value(
			"Account Closing Balance",
			{
				"account": "Sales - TPC",
				"cost_center": cost_center2,
				"period_closing_voucher": pcv2.name,
				"is_period_closing_voucher_entry": 0,
			},
			["credit", "credit_in_account_currency"],
			as_dict=1,
		)

		self.assertEqual(cc1_closing_balance.credit, 400)
		self.assertEqual(cc1_closing_balance.credit_in_account_currency, 400)
		self.assertEqual(cc2_closing_balance.credit, 500)
		self.assertEqual(cc2_closing_balance.credit_in_account_currency, 500)

		warehouse = frappe.db.get_value("Warehouse", {"company": company}, "name")

		repost_doc = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"company": company,
				"posting_date": "2020-03-15",
				"based_on": "Item and Warehouse",
				"item_code": "Test Item 1",
				"warehouse": warehouse,
			}
		)

		self.assertRaises(frappe.ValidationError, repost_doc.save)

		repost_doc.posting_date = today()
		repost_doc.save()

	def make_period_closing_voucher(
		self, posting_date, submit=True, period_start_date=None, period_end_date=None
	):
		surplus_account = create_account()
		cost_center = create_cost_center("Test Cost Center 1")
		fy = get_fiscal_year(posting_date, company="Test PCV Company")
		pcv = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": posting_date or today(),
				"period_start_date": period_start_date or fy[1],
				"period_end_date": period_end_date or fy[2],
				"company": "Test PCV Company",
				"fiscal_year": fy[0],
				"cost_center": cost_center,
				"closing_account_head": surplus_account,
				"remarks": "test",
			}
		)
		pcv.insert()
		if submit:
			pcv.submit()

		return pcv

	@change_settings(
		"Accounts Settings",
		{"enable_immutable_ledger": 1},
	)
	def test_immutable_ledger_reverse_entry_uses_passed_posting_date_after_pcv(self):
		frappe.db.sql("delete from `tabGL Entry` where company='Test PCV Company'")
		frappe.db.sql("delete from `tabPeriod Closing Voucher` where company='Test PCV Company'")

		company = create_company()
		cost_center = create_cost_center("Test Cost Center 1")

		jv = make_journal_entry(
			posting_date="2021-03-15",
			amount=400,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=cost_center,
			company=company,
			save=False,
		)
		jv.company = company
		jv.save()
		jv.submit()

		self.make_period_closing_voucher(posting_date="2021-03-31")

		frappe.db.set_single_value("Accounts Settings", "acc_frozen_upto", "2021-12-31")

		try:
			make_reverse_gl_entries(
				voucher_type="Journal Entry",
				voucher_no=jv.name,
			)
		finally:
			frappe.db.set_single_value("Accounts Settings", "acc_frozen_upto", None)

		totals_after_cancel = frappe.db.sql(
			"""
				select sum(debit) as total_debit, sum(credit) as total_credit
				from `tabGL Entry`
				where voucher_type=%s and voucher_no=%s and is_cancelled=0
			""",
			("Journal Entry", jv.name),
			as_dict=True,
		)[0]

		self.assertEqual(totals_after_cancel.total_debit, totals_after_cancel.total_credit)

	def make_income_entry(self, posting_date, amount, income_account="Sales - TPC"):
		return make_journal_entry(
			posting_date=posting_date,
			amount=amount,
			account1="Cash - TPC",
			account2=income_account,
			cost_center=create_cost_center("Test Cost Center 1"),
			company="Test PCV Company",
			submit=True,
		)

	def test_partly_closed_previous_year_blocks_closing_next_year(self):
		self.make_income_entry("2021-02-10", 1000)
		self.make_income_entry("2021-06-15", 700)
		self.make_period_closing_voucher(
			posting_date="2021-02-28", period_start_date="2021-01-01", period_end_date="2021-02-28"
		)

		with self.assertRaisesRegex(frappe.ValidationError, f"from <strong>{formatdate('2021-03-01')}"):
			self.make_period_closing_voucher(posting_date="2022-12-31")

		self.make_period_closing_voucher(
			posting_date="2021-12-31", period_start_date="2021-03-01", period_end_date="2021-12-31"
		)
		self.make_period_closing_voucher(posting_date="2022-12-31")

	def test_unclosed_earlier_year_blocks_closing(self):
		self.make_income_entry("2021-06-15", 500)

		with self.assertRaisesRegex(frappe.ValidationError, f"from <strong>{formatdate('2021-06-15')}"):
			self.make_period_closing_voucher(posting_date="2023-12-31")

		self.make_period_closing_voucher(posting_date="2021-12-31")
		self.make_period_closing_voucher(posting_date="2023-12-31")

	def make_period_closing_voucher_in_background(self, posting_date):
		with patch.object(frappe.db, "estimate_count", return_value=100_001), patch("frappe.enqueue"):
			return self.make_period_closing_voucher(posting_date=posting_date)

	def test_incomplete_previous_closing_blocks_next_closing(self):
		self.make_income_entry("2021-03-15", 1000)
		pending_pcv = self.make_period_closing_voucher_in_background(posting_date="2021-12-31")
		self.assertEqual(pending_pcv.gle_processing_status, "In Progress")

		with self.assertRaisesRegex(
			frappe.ValidationError, f"{pending_pcv.name}.*GL Entry Processing Status"
		):
			self.make_period_closing_voucher(posting_date="2022-12-31")

	def test_previous_closing_without_processing_status_allows_next_closing(self):
		self.make_income_entry("2021-03-15", 1000)
		previous_pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		previous_pcv.db_set("gle_processing_status", None)

		pcv = self.make_period_closing_voucher(posting_date="2022-12-31")
		self.assertEqual(pcv.docstatus, 1)

	def test_failed_previous_closing_blocks_next_closing(self):
		self.make_income_entry("2021-03-15", 1000)
		failed_pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		failed_pcv.db_set("gle_processing_status", "Failed")

		with self.assertRaisesRegex(frappe.ValidationError, f"{failed_pcv.name}.*GL Entry Processing Status"):
			self.make_period_closing_voucher(posting_date="2022-12-31")

	def test_closing_error_fails_submit_in_legacy_controller(self):
		self.make_income_entry("2021-03-15", 1000, income_account="Service - TPC")
		frappe.db.set_value("Account", "Service - TPC", "disabled", 1)

		pcv = self.make_period_closing_voucher(posting_date="2021-03-31", submit=False)
		with self.assertRaisesRegex(frappe.ValidationError, "disabled accounts"):
			pcv.submit()

	def test_closing_error_marks_voucher_failed_in_background_job(self):
		self.make_income_entry("2021-03-15", 1000, income_account="Service - TPC")
		frappe.db.set_value("Account", "Service - TPC", "disabled", 1)

		pcv = self.make_period_closing_voucher_in_background(posting_date="2021-03-31")
		process_gl_and_closing_entries(pcv)
		pcv.reload()

		self.assertEqual(pcv.gle_processing_status, "Failed")
		self.assertIn("disabled accounts", pcv.error_message)
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": pcv.name}))
		self.assertFalse(frappe.db.exists("Account Closing Balance", {"period_closing_voucher": pcv.name}))

	def make_sale_and_refund(self, posting_date, amount):
		self.make_income_entry(posting_date, amount)
		self.make_income_entry(posting_date, -amount)

	def assert_period_closed_without_entries(self, pcv):
		self.assertEqual(pcv.gle_processing_status, "Completed")
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": pcv.name}))

		late_entry = make_journal_entry(
			posting_date="2021-12-20",
			amount=100,
			account1="Cash - TPC",
			account2="Sales - TPC",
			cost_center=create_cost_center("Test Cost Center 1"),
			company="Test PCV Company",
		)
		self.assertRaisesRegex(frappe.ValidationError, "Books have been closed", late_entry.submit)

	def test_close_period_with_zero_profit_and_loss_in_legacy_controller(self):
		self.make_sale_and_refund("2021-03-15", 1000)
		pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		pcv.reload()
		self.assert_period_closed_without_entries(pcv)

	def get_balance_sheet_figure(self, account_name, period_end_date):
		from erpnext.accounts.report.balance_sheet.balance_sheet import execute
		from erpnext.accounts.report.financial_statements import get_period_list

		period_key = get_period_list(
			None, None, period_end_date, period_end_date, "Date Range", "Yearly", company="Test PCV Company"
		)[0].key
		filters = frappe._dict(
			company="Test PCV Company",
			period_start_date=period_end_date,
			period_end_date=period_end_date,
			periodicity="Yearly",
			filter_based_on="Date Range",
			accumulated_values=True,
		)
		return next(row[period_key] for row in execute(filters)[1] if row.get("account_name") == account_name)

	def get_gl_balance(self, account, to_date):
		return frappe.get_all(
			"GL Entry",
			filters={"account": account, "posting_date": ("<=", to_date), "is_cancelled": 0},
			fields=["sum(debit) as debit", "sum(credit) as credit"],
		)[0]

	@change_settings("Accounts Settings", {"enable_immutable_ledger": 1})
	def test_immutable_ledger_cancel_and_reclose_in_legacy_controller(self):
		self.make_income_entry("2021-03-15", 1000)
		pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		pcv.cancel()

		reversal_dates = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": pcv.name, "remarks": ("like", "On cancellation%")},
			pluck="posting_date",
			distinct=True,
		)
		self.assertEqual(reversal_dates, [getdate("2021-12-31")])

		new_pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		sales = self.get_gl_balance("Sales - TPC", "2021-12-31")
		self.assertEqual(flt(sales.debit) - flt(sales.credit), 0)
		self.assertEqual(self.get_balance_sheet_figure("Reserve and Surplus", "2021-12-31"), 1000)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry",
				{"voucher_no": new_pcv.name, "account": "Sales - TPC", "is_cancelled": 0},
				"debit",
			),
			1000,
		)

	@change_settings("Accounts Settings", {"frozen_accounts_modifier": None})
	def test_closing_account_must_be_usable_ledger_of_company(self):
		self.make_income_entry("2021-03-15", 1000)
		pcv = self.make_period_closing_voucher(posting_date="2021-12-31", submit=False)

		cases = [
			("Equity - TPC", {}, "cannot be a group account"),
			("Retained Earnings - _TC", {}, "does not belong to Company"),
			(pcv.closing_account_head, {"disabled": 1}, "is disabled"),
			(pcv.closing_account_head, {"disabled": 0, "freeze_account": "Yes"}, "is frozen"),
		]
		for account, values, message in cases:
			with self.subTest(account=account, values=values):
				if values:
					frappe.db.set_value("Account", account, values)

				pcv.reload()
				pcv.closing_account_head = account
				self.assertRaisesRegex(frappe.ValidationError, message, pcv.save)

	def make_foreign_currency_income_entry(self, posting_date, account, amount, exchange_rate):
		jv = frappe.new_doc("Journal Entry")
		jv.update({"posting_date": posting_date, "company": "Test PCV Company", "multi_currency": 1})
		income_side = "credit" if amount > 0 else "debit"
		cash_side = "debit" if amount > 0 else "credit"
		for row in (
			{"account": "Cash - TPC", f"{cash_side}_in_account_currency": abs(amount) * exchange_rate},
			{
				"account": account,
				"exchange_rate": exchange_rate,
				f"{income_side}_in_account_currency": abs(amount),
			},
		):
			jv.append("accounts", {**row, "cost_center": create_cost_center("Test Cost Center 1")})

		jv.submit()

	def get_account_currency_balance(self, account):
		balance = frappe.get_all(
			"GL Entry",
			filters={"account": account, "is_cancelled": 0},
			fields=[
				"sum(debit) as debit",
				"sum(credit) as credit",
				"sum(debit_in_account_currency) as debit_in_account_currency",
				"sum(credit_in_account_currency) as credit_in_account_currency",
			],
		)[0]
		return (
			flt(balance.debit) - flt(balance.credit),
			flt(balance.debit_in_account_currency) - flt(balance.credit_in_account_currency),
		)

	@change_settings("Accounts Settings", {"enable_immutable_ledger": 1})
	def test_close_foreign_currency_balance_in_legacy_controller(self):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Sales EUR",
				"parent_account": "Direct Income - TPC",
				"company": "Test PCV Company",
				"account_currency": "EUR",
			}
		).insert(ignore_if_duplicate=True)
		self.make_foreign_currency_income_entry("2021-03-15", account.name, 100, 80)
		self.make_foreign_currency_income_entry("2021-04-15", account.name, -80, 100)
		self.assertEqual(self.get_account_currency_balance(account.name), (0, -20))

		pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		self.assertEqual(pcv.gle_processing_status, "Completed")
		self.assertEqual(self.get_account_currency_balance(account.name), (0, 0))

		pcv.cancel()
		self.assertEqual(self.get_account_currency_balance(account.name), (0, -20))

	def test_future_closing_voucher_message_shows_full_name(self):
		self.make_income_entry("2021-03-15", 1000)
		pcv = self.make_period_closing_voucher(posting_date="2021-12-31")
		next_pcv = self.make_period_closing_voucher(posting_date="2022-12-31")

		self.assertRaisesRegex(
			frappe.ValidationError, f"Period Closing Entry {next_pcv.name} exists after", pcv.cancel
		)

	def test_period_dates_need_read_permission(self):
		from erpnext.assets.doctype.asset_activity.test_asset_activity import create_user_with_roles

		user = create_user_with_roles("pcv_stock_user@example.com", "Stock User")
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user)

		self.assertRaises(
			frappe.PermissionError, get_period_start_end_date, "_Test Fiscal Year 2021", "Test PCV Company"
		)

	def test_period_dates_need_permission_on_requested_company(self):
		from frappe.permissions import add_user_permission

		from erpnext.assets.doctype.asset_activity.test_asset_activity import create_user_with_roles

		user = create_user_with_roles("pcv_restricted_accounts_manager@example.com", "Accounts Manager")
		add_user_permission("Company", "_Test Company", user)

		with self.set_user(user):
			get_period_start_end_date("_Test Fiscal Year 2021", "_Test Company")
			self.assertRaises(
				frappe.PermissionError,
				get_period_start_end_date,
				"_Test Fiscal Year 2021",
				"Test PCV Company",
			)


def create_company():
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": "Test PCV Company",
			"country": "United States",
			"default_currency": "USD",
		}
	)
	company.insert(ignore_if_duplicate=True)
	return company.name


def create_account():
	account = frappe.get_doc(
		{
			"account_name": "Reserve and Surplus",
			"is_group": 0,
			"company": "Test PCV Company",
			"root_type": "Liability",
			"report_type": "Balance Sheet",
			"account_currency": "USD",
			"parent_account": "Current Liabilities - TPC",
			"doctype": "Account",
		}
	).insert(ignore_if_duplicate=True)
	return account.name


def create_cost_center(cc_name):
	costcenter = frappe.get_doc(
		{
			"company": "Test PCV Company",
			"cost_center_name": cc_name,
			"doctype": "Cost Center",
			"parent_cost_center": "Test PCV Company - TPC",
		}
	)
	costcenter.insert(ignore_if_duplicate=True)
	return costcenter.name


test_dependencies = ["Customer", "Cost Center"]
test_records = frappe.get_test_records("Period Closing Voucher")

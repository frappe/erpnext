# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.deferred_revenue import (
	build_conditions,
	convert_deferred_expense_to_expense,
	convert_deferred_revenue_to_income,
)
from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
	check_gl_entries,
	create_sales_invoice,
)
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.tests.utils import ERPNextTestSuite


class TestProcessDeferredAccounting(ERPNextTestSuite):
	def test_creation_of_ledger_entry_on_submit(self):
		"""test creation of gl entries on submission of document"""
		change_acc_settings(acc_frozen_till_date="2023-05-31", book_deferred_entries_based_on="Months")

		deferred_account = create_account(
			account_name="Deferred Revenue for Accounts Frozen",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)

		item = create_item("_Test Item for Deferred Accounting")
		item.enable_deferred_revenue = 1
		item.deferred_revenue_account = deferred_account
		item.no_of_months = 12
		item.save()

		si = create_sales_invoice(
			item=item.name, rate=3000, update_stock=0, posting_date="2023-07-01", do_not_submit=True
		)
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = "2023-05-01"
		si.items[0].service_end_date = "2023-07-31"
		si.items[0].deferred_revenue_account = deferred_account
		si.save()
		si.submit()

		original_gle = [
			["Debtors - _TC", 3000.0, 0, "2023-07-01"],
			[deferred_account, 0.0, 3000, "2023-07-01"],
		]

		check_gl_entries(self, si.name, original_gle, "2023-07-01")

		process_deferred_accounting = frappe.get_doc(
			doctype="Process Deferred Accounting",
			posting_date="2023-07-01",
			start_date="2023-05-01",
			end_date="2023-06-30",
			type="Income",
			company="_Test Company",
		)

		process_deferred_accounting.insert()
		process_deferred_accounting.submit()

		expected_gle = [
			["Debtors - _TC", 3000, 0.0, "2023-07-01"],
			[deferred_account, 0.0, 3000, "2023-07-01"],
			["Sales - _TC", 0.0, 1000, "2023-06-30"],
			[deferred_account, 1000, 0.0, "2023-06-30"],
			["Sales - _TC", 0.0, 1000, "2023-06-30"],
			[deferred_account, 1000, 0.0, "2023-06-30"],
		]

		check_gl_entries(self, si.name, expected_gle, "2023-07-01")

		# cancel the process deferred accounting document
		process_deferred_accounting.cancel()

		# check if gl entries are cancelled
		check_gl_entries(self, si.name, original_gle, "2023-07-01")
		change_acc_settings()

	def test_pda_submission_and_cancellation(self):
		pda = frappe.get_doc(
			doctype="Process Deferred Accounting",
			posting_date="2019-01-01",
			start_date="2019-01-01",
			end_date="2019-01-31",
			type="Income",
			company="_Test Company",
		)
		pda.submit()
		pda.cancel()

	def test_account_of_another_company_is_rejected(self):
		for process_type, parent_account in (
			("Income", "Current Liabilities - _TC1"),
			("Expense", "Current Assets - _TC1"),
		):
			with self.subTest(process_type=process_type):
				account = create_deferred_account(process_type, "_Test Company 1", parent_account)
				pda = make_process_deferred_accounting(process_type, "_Test Company", account=account)

				self.assertRaises(frappe.ValidationError, pda.insert)

	def test_revenue_account_filter_books_only_invoices_of_the_company(self):
		account = create_deferred_account("Income", "_Test Company 1", "Current Liabilities - _TC1")
		si = make_deferred_sales_invoice_for_test_company_1(account)
		pda = make_process_deferred_accounting("Income", "_Test Company").insert()

		conditions = build_conditions("Income", account, "_Test Company")
		convert_deferred_revenue_to_income(pda.name, "2023-05-01", "2023-06-30", conditions)
		self.assertFalse(get_deferred_gl_entries(si.name))

		conditions = build_conditions("Income", account, "_Test Company 1")
		convert_deferred_revenue_to_income(pda.name, "2023-05-01", "2023-06-30", conditions)
		self.assertTrue(get_deferred_gl_entries(si.name))

	def test_expense_account_filter_books_only_invoices_of_the_company(self):
		account = create_deferred_account("Expense", "_Test Company 1", "Current Assets - _TC1")
		pi = make_deferred_purchase_invoice_for_test_company_1(account)
		pda = make_process_deferred_accounting("Expense", "_Test Company").insert()

		conditions = build_conditions("Expense", account, "_Test Company")
		convert_deferred_expense_to_expense(pda.name, "2023-05-01", "2023-06-30", conditions)
		self.assertFalse(get_deferred_gl_entries(pi.name))

		conditions = build_conditions("Expense", account, "_Test Company 1")
		convert_deferred_expense_to_expense(pda.name, "2023-05-01", "2023-06-30", conditions)
		self.assertTrue(get_deferred_gl_entries(pi.name))


def create_deferred_account(process_type, company, parent_account):
	return create_account(
		account_name=f"_Test Deferred {process_type} for Company Filter",
		parent_account=parent_account,
		company=company,
	)


def make_process_deferred_accounting(process_type, company, account=None):
	return frappe.get_doc(
		doctype="Process Deferred Accounting",
		posting_date="2023-07-01",
		start_date="2023-05-01",
		end_date="2023-06-30",
		type=process_type,
		company=company,
		account=account,
	)


def make_deferred_sales_invoice_for_test_company_1(deferred_account):
	si = create_sales_invoice(
		company="_Test Company 1",
		debit_to="Debtors - _TC1",
		cost_center="Main - _TC1",
		income_account="Sales - _TC1",
		expense_account="Cost of Goods Sold - _TC1",
		warehouse="Stores - _TC1",
		currency="USD",
		rate=3000,
		posting_date="2023-07-01",
		do_not_submit=True,
	)
	si.items[0].enable_deferred_revenue = 1
	si.items[0].service_start_date = "2023-05-01"
	si.items[0].service_end_date = "2023-07-31"
	si.items[0].deferred_revenue_account = deferred_account
	si.save()
	return si.submit()


def make_deferred_purchase_invoice_for_test_company_1(deferred_account):
	item = create_item("_Test Non Stock Item for Deferred Expense", is_stock_item=0, is_purchase_item=True)
	pi = make_purchase_invoice(
		company="_Test Company 1",
		item=item.name,
		qty=1,
		rate=3000,
		currency="USD",
		cost_center="Main - _TC1",
		expense_account="Cost of Goods Sold - _TC1",
		warehouse="Stores - _TC1",
		do_not_save=True,
	)
	pi.set_posting_time = 1
	pi.posting_date = "2023-07-01"
	pi.items[0].enable_deferred_expense = 1
	pi.items[0].service_start_date = "2023-05-01"
	pi.items[0].service_end_date = "2023-07-31"
	pi.items[0].deferred_expense_account = deferred_account
	pi.save()
	return pi.submit()


def get_deferred_gl_entries(voucher_no):
	return frappe.get_all(
		"GL Entry",
		filters={
			"voucher_no": voucher_no,
			"against_voucher_type": "Process Deferred Accounting",
			"is_cancelled": 0,
		},
		pluck="name",
	)


def change_acc_settings(
	company="_Test Company", acc_frozen_till_date=None, book_deferred_entries_based_on="Days"
):
	acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
	acc_settings.book_deferred_entries_based_on = book_deferred_entries_based_on
	frappe.db.set_value("Company", company, "accounts_frozen_till_date", acc_frozen_till_date)
	acc_settings.save()

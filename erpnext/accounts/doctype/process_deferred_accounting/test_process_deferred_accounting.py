# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from datetime import date

import frappe
from frappe.utils import (
	add_months,
	add_years,
	get_first_day,
	get_last_day,
	getdate,
	nowdate,
)

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
from erpnext.accounts.doctype.payment_reconciliation.test_payment_reconciliation import create_fiscal_year
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
	check_gl_entries,
	create_sales_invoice,
)
from erpnext.controllers.tests.test_accounts_controller import make_supplier
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.utils import get_or_create_fiscal_year


class TestProcessDeferredAccounting(unittest.TestCase):
	def setUp(self):
		create_company()
		get_or_create_fiscal_year("_Test Company")
		backdate = getdate(add_years(nowdate(), -2))
		create_fiscal_year("_Test Company", date(backdate.year, 1, 1), date(backdate.year, 12, 31))

	def test_creation_of_ledger_entry_on_submit(self):
		"""test creation of gl entries on submission of document"""
		change_acc_settings(acc_frozen_upto="2023-05-31", book_deferred_entries_based_on="Months")

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

		process_deferred_accounting = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date="2023-07-01",
				start_date="2023-05-01",
				end_date="2023-06-30",
				type="Income",
			)
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
		change_acc_settings()

	def test_auto_deferred_expense_entries_TC_ACC_092(self):
		"""Test automatic deferred expense entries on submission and monthly write-off."""
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice

		supplier = make_supplier("_Test Supplier", currency="INR")

		# Step 1: Set dynamic dates (2 years back)
		backdate = getdate(add_years(nowdate(), -1))
		start_date = get_first_day(add_months(backdate, 4))
		end_date = get_last_day(add_months(backdate, 6))
		posting_date = get_first_day(add_months(backdate, 6))
		create_fiscal_year("_Test Company", date(posting_date.year, 1, 1), date(posting_date.year, 12, 31))
		# Step 2: Set Accounting Settings
		change_acc_settings(acc_frozen_upto=start_date, book_deferred_entries_based_on="Months")

		# Step 3: Create Deferred Expense Account
		deferred_account = create_account(
			account_name="Deferred Expense", parent_account="Current Assets - _TC", company="_Test Company"
		)

		# Step 4: Configure Accounting Settings
		acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		acc_settings.book_deferred_entries_via_journal_entry = 1
		acc_settings.submit_journal_entries = 1
		acc_settings.save()

		# Step 5: Create Item with Deferred Expense
		item = create_item(
			"_Test Item for Deferred Accounting", warehouse="Stores - _TC", is_purchase_item=True
		)
		item.enable_deferred_expense = 1
		item.item_defaults[0].deferred_expense_account = deferred_account
		if frappe.db.has_column("Item", "gst_hsn_code"):
			item.gst_hsn_code = "01011010"
		item.save()

		# Step 6: Create Purchase Invoice
		pi = make_purchase_invoice(
			supplier=supplier,
			item=item.name,
			uom="Nos",
			qty=1,
			rate=100,
			warehouse="Stores - _TC",
			cost_center="Main - _TC",
			expense_account="Cost of Goods Sold - _TC",
			supplier_warehouse="Stores - _TC",
			do_not_save=True,
		)
		pi.set_posting_time = 1
		pi.posting_date = posting_date
		pi.items[0].enable_deferred_expense = 1
		pi.items[0].service_start_date = start_date
		pi.items[0].service_end_date = end_date
		pi.items[0].deferred_expense_account = deferred_account
		# pi.flags.ignore_validate = True
		# pi.flags.ignore_mandatory=True
		pi.save()
		pi.submit()

		# Step 7: Process Deferred Expense (First Entry)
		process_deferred_expense = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=posting_date,
				start_date=start_date,
				end_date=end_date,
				type="Expense",
				company="_Test Company",
			)
		)
		process_deferred_expense.insert()
		process_deferred_expense.submit()

		# Step 8: Check Initial General Ledger Entry
		initial_gle = [
			[deferred_account, 6000, 0.0, posting_date],
			["Creditors - _TC", 0.0, 6000, posting_date],
		]
		check_gl_entries(self, pi.name, initial_gle, posting_date)

		# Step 9: Process First Month's Deferred Expense Entry
		first_month_posting_date = get_last_day(posting_date)
		process_deferred_expense = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=first_month_posting_date,
				start_date=start_date,
				end_date=end_date,
				type="Expense",
			)
		)

		process_deferred_expense.insert()
		process_deferred_expense.submit()

		# Step 10: Check Monthly Write-Off General Ledger Entry
		monthly_gle = [
			["Expense - _TC", 1000, 0.0, first_month_posting_date],
			[deferred_account, 0.0, 1000, first_month_posting_date],
		]
		check_gl_entries(self, pi.name, monthly_gle, first_month_posting_date)

		# Step 11: Verify No Unexpected GL Entries for Remaining Months
		for month_offset in range(1, 6):
			month_end_date = get_last_day(add_months(posting_date, month_offset))
			check_gl_entries(
				self,
				pi.name,
				[
					["Expense - _TC", 1000, 0.0, month_end_date],
					[deferred_account, 0.0, 1000, month_end_date],
				],
				month_end_date,
			)

		change_acc_settings()

	def test_auto_deferred_revenue_TC_ACC_093(self):
		"""Test auto deferred revenue on a monthly basis."""
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_customer
		from erpnext.controllers.tests.test_accounts_controller import make_supplier

		customer = create_customer("_Test Customer", currency="INR")

		base_date = getdate(add_years(nowdate(), -1))
		start_date = get_first_day(add_months(base_date, 4))
		end_date = get_last_day(add_months(base_date, 6))
		posting_date = get_first_day(add_months(base_date, 6))
		acc_frozen_upto = get_last_day(add_months(base_date, 3))
		create_fiscal_year("_Test Company",date(base_date.year,1,1),date(base_date.year,12,31))
		# Step 2: Set Accounting Settings
		change_acc_settings(acc_frozen_upto=acc_frozen_upto, book_deferred_entries_based_on="Months")

		# Step 3: Create Deferred Revenue Account
		deferred_account = create_account(
			account_name="Deferred Revenue for Accounts Frozen",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)

		# Step 4: Create Item with Deferred Revenue
		item = create_item("_Test Item for Deferred Accounting")
		item.enable_deferred_revenue = 1
		item.deferred_revenue_account = deferred_account
		item.no_of_months = 12
		if frappe.db.has_column("Item", "gst_hsn_code"):
			item.gst_hsn_code = "01011010"
		item.save(ignore_permissions=True)

		# Step 5: Create Sales Invoice
		si = create_sales_invoice(
			customer=customer,
			item=item.name,
			rate=3000,
			update_stock=0,
			uom="Nos",
			warehouse="Stores - _TC",
			cost_center="Main - _TC",
			posting_date=posting_date,
			do_not_submit=True,
		)
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = start_date
		si.items[0].service_end_date = end_date
		si.items[0].deferred_revenue_account = deferred_account
		si.save()
		si.submit()

		# Step 6: Process Deferred Accounting
		process_deferred_accounting = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=posting_date,
				start_date=start_date,
				end_date=get_last_day(add_months(posting_date, -1)),  # One month before posting date
				type="Income",
			)
		)

		process_deferred_accounting.insert()
		process_deferred_accounting.submit()

		# Step 7: Validate General Ledger Entries
		expected_gle = [
			["Debtors - _TC", 3000, 0.0, posting_date],
			[deferred_account, 0.0, 3000, posting_date],
			["Sales - _TC", 0.0, 1000, end_date],
			[deferred_account, 1000, 0.0, end_date],
			["Sales - _TC", 0.0, 1000, end_date],
			[deferred_account, 1000, 0.0, end_date],
		]
		check_gl_entries(self, si.name, expected_gle, posting_date)

		# Step 8: Reset Accounting Settings
		change_acc_settings()

	def test_pda_submission_and_cancellation(self):
		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date="2019-01-01",
				start_date="2019-01-01",
				end_date="2019-01-31",
				type="Income",
			)
		)
		pda.submit()
		pda.cancel()


def change_acc_settings(acc_frozen_upto="", book_deferred_entries_based_on="Days"):
	acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
	acc_settings.acc_frozen_upto = acc_frozen_upto
	acc_settings.book_deferred_entries_based_on = book_deferred_entries_based_on
	acc_settings.save()

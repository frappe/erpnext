# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
	check_gl_entries,
	create_sales_invoice,
)
from erpnext.stock.doctype.item.test_item import create_item


class TestProcessDeferredAccounting(IntegrationTestCase):
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

		# cancel the process deferred accounting document
		process_deferred_accounting.cancel()

		# check if gl entries are cancelled
		check_gl_entries(self, si.name, original_gle, "2023-07-01")
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


def change_acc_settings(
	company="_Test Company", acc_frozen_till_date=None, book_deferred_entries_based_on="Days"
):
	acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
	acc_settings.book_deferred_entries_based_on = book_deferred_entries_based_on
	frappe.db.set_value("Company", company, "accounts_frozen_till_date", acc_frozen_till_date)
	acc_settings.save()

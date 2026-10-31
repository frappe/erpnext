# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest import mock

import frappe

from erpnext.accounts.doctype.account.test_account import create_account
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

	def make_deferred_invoice(self, start, end, rate=3000):
		deferred_account = create_account(
			account_name="Deferred Revenue for Process Tests",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)
		item = create_item("_Test Item for Deferred Process")
		item.enable_deferred_revenue = 1
		item.deferred_revenue_account = deferred_account
		item.no_of_months = 12
		item.save()

		si = create_sales_invoice(item=item.name, rate=rate, posting_date=start, do_not_submit=True)
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = start
		si.items[0].service_end_date = end
		si.items[0].deferred_revenue_account = deferred_account
		si.save()
		si.submit()
		return si

	def run_process(self, start, end):
		pda = frappe.get_doc(
			doctype="Process Deferred Accounting",
			posting_date=end,
			start_date=start,
			end_date=end,
			type="Income",
			company="_Test Company",
		)
		pda.insert()
		pda.submit()
		return pda

	def booked_income(self, invoice):
		return sum(
			frappe.get_all(
				"GL Entry",
				filters={"voucher_no": invoice, "account": "Sales - _TC", "is_cancelled": 0},
				pluck="credit",
			)
		)

	@ERPNextTestSuite.change_settings("Accounts Settings", {"book_deferred_entries_based_on": "Months"})
	def test_two_day_service_across_a_month_end(self):
		si = self.make_deferred_invoice("2023-05-31", "2023-06-01")

		self.run_process("2023-05-01", "2023-06-30")

		self.assertEqual(self.booked_income(si.name), 3000)

	def test_failing_invoice_does_not_stop_the_others(self):
		from erpnext.accounts import general_ledger

		failing = self.make_deferred_invoice("2023-01-01", "2023-03-31")
		other = self.make_deferred_invoice("2023-01-01", "2023-03-31")
		make_gl_entries = general_ledger.make_gl_entries

		def fail_for_one_invoice(gl_map, *args, **kwargs):
			if gl_map and gl_map[0].voucher_no == failing.name:
				raise frappe.ValidationError("Booking failed")
			return make_gl_entries(gl_map, *args, **kwargs)

		with (
			mock.patch.object(general_ledger, "make_gl_entries", side_effect=fail_for_one_invoice),
			mock.patch.object(frappe, "in_test", False),
			mock.patch.object(frappe.db, "commit"),
			mock.patch("erpnext.accounts.deferred_revenue.send_mail") as send_mail,
		):
			pda = self.run_process("2023-01-01", "2023-03-31")
		frappe.flags.deferred_accounting_error = False

		self.assertTrue(frappe.db.exists("Process Deferred Accounting", pda.name))
		self.assertFalse(self.booked_income(failing.name))
		self.assertEqual(self.booked_income(other.name), 3000)
		send_mail.assert_called_once()

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"book_deferred_entries_via_journal_entry": 1, "submit_journal_entries": 0}
	)
	def test_cancel_deletes_draft_journals(self):
		self.make_deferred_invoice("2023-01-01", "2023-01-31")
		pda = self.run_process("2023-01-01", "2023-01-31")
		self.assertTrue(frappe.db.exists("Journal Entry", {"process_deferred_accounting": pda.name}))

		pda.cancel()

		self.assertFalse(frappe.db.exists("Journal Entry", {"process_deferred_accounting": pda.name}))


def change_acc_settings(
	company="_Test Company", acc_frozen_till_date=None, book_deferred_entries_based_on="Days"
):
	acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
	acc_settings.book_deferred_entries_based_on = book_deferred_entries_based_on
	frappe.db.set_value("Company", company, "accounts_frozen_till_date", acc_frozen_till_date)
	acc_settings.save()

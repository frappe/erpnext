# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
	aggregate_with_last_account_closing_balance,
	generate_key,
	make_closing_entries,
)
from erpnext.tests.utils import ERPNextTestSuite


def entry(**overrides):
	row = {"debit": 0, "credit": 0, "debit_in_account_currency": 0, "credit_in_account_currency": 0}
	row.update(overrides)
	return row


class TestAccountClosingBalance(ERPNextTestSuite):
	"""The closing-balance snapshot is built by merging this period's entries with the
	previous period's. These lock the merge/key logic that drives that carry-forward."""

	def test_matching_entries_are_summed(self):
		# this is how a prior-period balance carries forward into the current one
		merged = aggregate_with_last_account_closing_balance(
			[
				entry(account="Cash - _TC", debit=100, debit_in_account_currency=100),
				entry(
					account="Cash - _TC",
					debit=50,
					credit=20,
					debit_in_account_currency=50,
					credit_in_account_currency=20,
				),
			],
			[],
		)
		self.assertEqual(len(merged), 1)
		row = next(iter(merged.values()))
		self.assertEqual(row["debit"], 150)
		self.assertEqual(row["credit"], 20)
		# the account-currency columns are accumulated in the same pass
		self.assertEqual(row["debit_in_account_currency"], 150)
		self.assertEqual(row["credit_in_account_currency"], 20)

	def test_entries_are_kept_separate_per_dimension(self):
		merged = aggregate_with_last_account_closing_balance(
			[
				entry(account="Cash - _TC", cost_center="CC1", debit=100, debit_in_account_currency=100),
				entry(account="Cash - _TC", cost_center="CC2", debit=40, debit_in_account_currency=40),
			],
			[],
		)
		self.assertEqual(len(merged), 2)

	def test_period_closing_flag_is_part_of_the_key(self):
		# a P&L reversal (flag 0) and a closing-account entry (flag 1) for the same
		# account must not merge, so the flag has to distinguish their keys
		key_reversal, _ = generate_key(entry(account="Sales - _TC", is_period_closing_voucher_entry=0), [])
		key_closing, _ = generate_key(entry(account="Sales - _TC", is_period_closing_voucher_entry=1), [])
		self.assertNotEqual(key_reversal, key_closing)

	def test_closing_entries_are_bulk_inserted(self):
		# a PCV can make one row per dimension combination; one write per row
		# breaks the write limit of the transaction
		writes_before = frappe.db.transaction_writes
		make_test_closing_entries(500)

		self.assertLess(frappe.db.transaction_writes - writes_before, 5)
		rows = get_test_closing_balances()
		self.assertEqual(len(rows), 500)
		self.assertTrue(all(row.debit == 10 and row.docstatus == 1 for row in rows))
		self.assertEqual({str(row.closing_date) for row in rows}, {"1990-12-31"})

	def test_reporting_currency_rate_is_fetched_once(self):
		company = "_Test Company"
		frappe.db.set_value("Company", company, "reporting_currency", "USD")
		frappe.clear_document_cache("Company", company)
		self.addCleanup(frappe.clear_document_cache, "Company", company)

		module = "erpnext.accounts.doctype.account_closing_balance.account_closing_balance"
		with patch(f"{module}.get_exchange_rate", return_value=2) as get_exchange_rate:
			make_test_closing_entries(3)

		get_exchange_rate.assert_called_once()
		rows = get_test_closing_balances()
		self.assertEqual(len(rows), 3)
		for row in rows:
			self.assertEqual(row.reporting_currency_exchange_rate, 2)
			self.assertEqual(row.debit_in_reporting_currency, 20)
			self.assertEqual(row.credit_in_reporting_currency, 0)


def make_test_closing_entries(count):
	closing_entries = [
		entry(
			company="_Test Company",
			account="_Test Bank - _TC",
			project=f"_Test Dimension Value {i}",
			debit=10,
			debit_in_account_currency=10,
		)
		for i in range(count)
	]
	make_closing_entries(closing_entries, "_Test Closing Voucher", "_Test Company", "1990-12-31")


def get_test_closing_balances():
	return frappe.get_all(
		"Account Closing Balance",
		filters={"period_closing_voucher": "_Test Closing Voucher"},
		fields=[
			"debit",
			"docstatus",
			"closing_date",
			"reporting_currency_exchange_rate",
			"debit_in_reporting_currency",
			"credit_in_reporting_currency",
		],
	)

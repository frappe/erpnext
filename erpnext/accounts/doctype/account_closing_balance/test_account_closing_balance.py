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

	def test_reporting_amount_of_carried_balance_keeps_its_rate(self):
		module = "erpnext.accounts.doctype.account_closing_balance.account_closing_balance"
		previous = entry(
			company="_Test Company",
			account="Sales - _TC",
			credit=1000,
			credit_in_account_currency=1000,
			credit_in_reporting_currency=12,
		)
		current = frappe._dict(
			entry(company="_Test Company", account="Sales - _TC", credit=500, credit_in_account_currency=500)
		)

		with (
			patch(f"{module}.get_previous_closing_entries", return_value=[previous]),
			patch(f"{module}.get_reporting_currency_exchange_rate", return_value=0.01),
		):
			make_closing_entries([current], "ACB-TEST-PCV", "_Test Company", "2025-05-31")

		self.assertEqual(
			frappe.db.get_value(
				"Account Closing Balance",
				{"period_closing_voucher": "ACB-TEST-PCV"},
				["credit", "credit_in_reporting_currency"],
			),
			(1500, 17),
		)

# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
	aggregate_with_last_account_closing_balance,
	generate_key,
	make_closing_entries,
)


def entry(**overrides):
	row = {"debit": 0, "credit": 0, "debit_in_account_currency": 0, "credit_in_account_currency": 0}
	row.update(overrides)
	return row


class TestAccountClosingBalance(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

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

	def test_closing_entries_do_not_write_one_row_at_a_time(self):
		# one row per dimension value: a per-row insert hits max_writes_per_transaction on large sites
		entries = [
			frappe._dict(
				company="_Test Company",
				account="_Test Bank - _TC",
				account_currency="INR",
				cost_center="_Test Cost Center - _TC",
				project=f"_Test Dimension Value {i}",
				debit=10,
				credit=0,
				debit_in_account_currency=10,
				credit_in_account_currency=0,
				is_period_closing_voucher_entry=0,
			)
			for i in range(500)
		]

		writes = frappe.db.transaction_writes
		make_closing_entries(entries, "_Test Closing Voucher", "_Test Company", "1990-12-31")

		self.assertLess(frappe.db.transaction_writes - writes, 5)
		rows = frappe.get_all(
			"Account Closing Balance",
			{"period_closing_voucher": "_Test Closing Voucher"},
			["project", "debit", "closing_date", "docstatus"],
		)
		self.assertEqual(len(rows), 500)
		self.assertTrue(all(r.debit == 10 and r.docstatus == 1 for r in rows))
		self.assertEqual(str(rows[0].closing_date), "1990-12-31")

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.report.share_ledger.share_ledger import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"

# The report returns legacy positional columns (no fieldnames); name the indices once
# here so a column reorder needs a single edit instead of silently shifting assertions.
COL_SHAREHOLDER = 0
COL_DATE = 1
COL_TRANSFER_TYPE = 2
COL_SHARE_TYPE = 3
COL_NO_OF_SHARES = 4
COL_RATE = 5
COL_AMOUNT = 6
COL_COMPANY = 7
COL_SHARE_TRANSFER = 8


class TestShareLedger(ERPNextTestSuite):
	def setUp(self):
		self.shareholder = self.create_shareholder("_Test Share Ledger Holder")
		# Issue 100 shares on 2026-06-01, then another 50 on 2026-06-10.
		self.first = self.issue_shares(date="2026-06-01", from_no=1, to_no=100, rate=10)
		self.second = self.issue_shares(date="2026-06-10", from_no=101, to_no=150, rate=12)

	def test_ledger_lists_all_transfers_upto_date(self):
		data = self.run_report(shareholder=self.shareholder, date="2026-06-30")

		self.assertEqual(len(data), 2)

		first_row, second_row = data
		self.assertEqual(first_row[COL_SHAREHOLDER], self.shareholder)
		self.assertEqual(first_row[COL_DATE], frappe.utils.getdate("2026-06-01"))
		self.assertEqual(first_row[COL_TRANSFER_TYPE], "Issue")
		self.assertEqual(first_row[COL_SHARE_TYPE], "Equity")
		self.assertEqual(first_row[COL_NO_OF_SHARES], 100)
		self.assertEqual(first_row[COL_RATE], 10)
		self.assertEqual(first_row[COL_AMOUNT], 1000)
		self.assertEqual(first_row[COL_COMPANY], COMPANY)
		self.assertEqual(first_row[COL_SHARE_TRANSFER], self.first)

		self.assertEqual(second_row[COL_DATE], frappe.utils.getdate("2026-06-10"))
		self.assertEqual(second_row[COL_NO_OF_SHARES], 50)
		self.assertEqual(second_row[COL_RATE], 12)
		self.assertEqual(second_row[COL_AMOUNT], 600)
		self.assertEqual(second_row[COL_SHARE_TRANSFER], self.second)

	def test_running_balance_of_shares(self):
		data = self.run_report(shareholder=self.shareholder, date="2026-06-30")

		# The ledger records each transfer's raw no_of_shares (always positive); it does
		# not sign by direction. With only incoming "Issue" rows here, summing them is a
		# valid running total. (Directional balances are the Share Balance report's job.)
		running = 0
		balances = []
		for row in data:
			running += row[COL_NO_OF_SHARES]
			balances.append(running)

		self.assertEqual(balances, [100, 150])

	def test_as_on_date_between_transfers_shows_only_first(self):
		data = self.run_report(shareholder=self.shareholder, date="2026-06-05")

		self.assertEqual(len(data), 1)
		self.assertEqual(data[0][COL_SHARE_TRANSFER], self.first)
		self.assertEqual(data[0][COL_NO_OF_SHARES], 100)

	def test_transfer_type_label_when_shareholder_is_seller(self):
		buyer = self.create_shareholder("_Test Share Ledger Buyer")
		transfer = self.make_transfer(
			from_shareholder=self.shareholder,
			to_shareholder=buyer,
			date="2026-06-15",
			from_no=1,
			to_no=40,
			rate=10,
		)

		row = self.transfer_row(self.run_report(shareholder=self.shareholder, date="2026-06-30"), transfer)
		# seller side: the label names the counterparty it went "to"
		self.assertEqual(row[COL_TRANSFER_TYPE], f"Transfer to {buyer}")

	def test_transfer_type_label_when_shareholder_is_buyer(self):
		seller = self.create_shareholder("_Test Share Ledger Seller")
		# the seller must own shares before it can transfer them
		self.issue_shares(date="2026-06-12", from_no=201, to_no=300, rate=10, shareholder=seller)
		transfer = self.make_transfer(
			from_shareholder=seller,
			to_shareholder=self.shareholder,
			date="2026-06-15",
			from_no=201,
			to_no=240,
			rate=10,
		)

		row = self.transfer_row(self.run_report(shareholder=self.shareholder, date="2026-06-30"), transfer)
		# buyer side: the label names the counterparty it came "from"
		self.assertEqual(row[COL_TRANSFER_TYPE], f"Transfer from {seller}")

	def test_missing_date_throws(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict(shareholder=self.shareholder))

	def test_missing_shareholder_returns_no_rows(self):
		data = self.run_report(date="2026-06-30")
		self.assertEqual(data, [])

	def run_report(self, **extra):
		filters = frappe._dict({"company": COMPANY, **extra})
		return execute(filters)[1]

	def transfer_row(self, data, transfer_name):
		row = next((r for r in data if r[COL_SHARE_TRANSFER] == transfer_name), None)
		self.assertIsNotNone(row, f"Share Transfer {transfer_name} missing from ledger")
		return row

	def create_shareholder(self, title):
		doc = frappe.get_doc(
			{
				"doctype": "Shareholder",
				"title": title,
				"company": COMPANY,
			}
		).insert()
		return doc.name

	def issue_shares(self, date, from_no, to_no, rate, shareholder=None):
		doc = frappe.get_doc(
			{
				"doctype": "Share Transfer",
				"transfer_type": "Issue",
				"date": date,
				"to_shareholder": shareholder or self.shareholder,
				"share_type": "Equity",
				"from_no": from_no,
				"to_no": to_no,
				"no_of_shares": to_no - from_no + 1,
				"rate": rate,
				"company": COMPANY,
				"asset_account": "Cash - _TC",
				"equity_or_liability_account": "Creditors - _TC",
			}
		)
		doc.submit()
		return doc.name

	def make_transfer(self, from_shareholder, to_shareholder, date, from_no, to_no, rate):
		doc = frappe.get_doc(
			{
				"doctype": "Share Transfer",
				"transfer_type": "Transfer",
				"date": date,
				"from_shareholder": from_shareholder,
				"to_shareholder": to_shareholder,
				"share_type": "Equity",
				"from_no": from_no,
				"to_no": to_no,
				"no_of_shares": to_no - from_no + 1,
				"rate": rate,
				"company": COMPANY,
				"asset_account": "Cash - _TC",
				"equity_or_liability_account": "Creditors - _TC",
			}
		)
		doc.submit()
		return doc.name

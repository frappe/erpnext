# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.report.share_balance.share_balance import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"


class TestShareBalanceReport(ERPNextTestSuite):
	def setUp(self):
		self.share_type = create_share_type("_Test Share Balance Equity")
		self.shareholder = create_shareholder("_Test Share Balance Holder", COMPANY)

	def test_date_filter_is_mandatory(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict({"shareholder": self.shareholder}))

	def test_no_shareholder_returns_empty_data(self):
		# `shareholder` is optional; without it the report yields no rows.
		columns, data = execute(frappe._dict({"date": "2026-06-01", "company": COMPANY}))
		self.assertEqual(data, [])
		self.assertEqual(len(columns), 5)

	def test_balance_after_issue(self):
		create_share_transfer(
			transfer_type="Issue",
			to_shareholder=self.shareholder,
			share_type=self.share_type,
			from_no=1,
			to_no=100,
			no_of_shares=100,
			rate=10,
			date="2026-06-01",
		)

		row = self.get_row(date="2026-06-05")
		self.assertEqual(row[0], self.shareholder)
		self.assertEqual(row[1], self.share_type)
		self.assertEqual(row[2], 100)  # no_of_shares
		self.assertEqual(row[3], 10)  # average rate
		self.assertEqual(row[4], 1000)  # amount = 100 * 10

	def test_company_filter_scopes_transfers(self):
		# the transfer is booked under `_Test Company`
		create_share_transfer(
			transfer_type="Issue",
			to_shareholder=self.shareholder,
			share_type=self.share_type,
			from_no=1,
			to_no=100,
			no_of_shares=100,
			rate=10,
			date="2026-06-01",
		)

		# matching company: the holding shows up
		self.assertEqual(self.get_row(date="2026-06-05")[2], 100)

		# a different company must not surface this shareholder's transfer
		other_company_data = execute(
			frappe._dict(
				{"date": "2026-06-05", "company": "_Test Company 1", "shareholder": self.shareholder}
			)
		)[1]
		self.assertEqual(other_company_data, [])

	def test_balance_increases_on_second_issue(self):
		create_share_transfer(
			transfer_type="Issue",
			to_shareholder=self.shareholder,
			share_type=self.share_type,
			from_no=1,
			to_no=100,
			no_of_shares=100,
			rate=10,
			date="2026-06-01",
		)
		create_share_transfer(
			transfer_type="Issue",
			to_shareholder=self.shareholder,
			share_type=self.share_type,
			from_no=101,
			to_no=200,
			no_of_shares=100,
			rate=20,
			date="2026-06-10",
		)

		# The report groups by share type, summing shares and amount and
		# recomputing the average rate: (1000 + 2000) / 200 = 15.
		row = self.get_row(date="2026-06-15")
		self.assertEqual(row[2], 200)
		self.assertEqual(row[3], 15)
		self.assertEqual(row[4], 3000)

	def test_balance_reduces_after_transfer_out(self):
		other_holder = create_shareholder("_Test Share Balance Holder 2", COMPANY)
		create_share_transfer(
			transfer_type="Issue",
			to_shareholder=self.shareholder,
			share_type=self.share_type,
			from_no=1,
			to_no=100,
			no_of_shares=100,
			rate=10,
			date="2026-06-01",
		)
		create_share_transfer(
			transfer_type="Transfer",
			from_shareholder=self.shareholder,
			to_shareholder=other_holder,
			share_type=self.share_type,
			from_no=1,
			to_no=40,
			no_of_shares=40,
			rate=10,
			date="2026-06-10",
		)

		row = self.get_row(date="2026-06-15")
		self.assertEqual(row[2], 60)  # 100 issued - 40 transferred out
		self.assertEqual(row[4], 600)

		other_row = self.get_row(date="2026-06-15", shareholder=other_holder)
		self.assertEqual(other_row[2], 40)
		self.assertEqual(other_row[4], 400)

	def test_as_on_date_before_issue_shows_no_holding(self):
		# the report is as-on `date`: before any share transfer, the shareholder holds nothing
		create_share_transfer(
			transfer_type="Issue",
			to_shareholder=self.shareholder,
			share_type=self.share_type,
			from_no=1,
			to_no=100,
			no_of_shares=100,
			rate=10,
			date="2026-06-01",
		)

		data = execute(
			frappe._dict({"date": "2026-05-01", "company": COMPANY, "shareholder": self.shareholder})
		)[1]
		self.assertEqual(data, [])

	def test_as_on_date_reflects_holding_up_to_that_date(self):
		# two issues on different dates; an as-on date between them sees only the first
		create_share_transfer(
			transfer_type="Issue",
			to_shareholder=self.shareholder,
			share_type=self.share_type,
			from_no=1,
			to_no=100,
			no_of_shares=100,
			rate=10,
			date="2026-06-01",
		)
		create_share_transfer(
			transfer_type="Issue",
			to_shareholder=self.shareholder,
			share_type=self.share_type,
			from_no=101,
			to_no=200,
			no_of_shares=100,
			rate=20,
			date="2026-06-10",
		)

		self.assertEqual(self.get_row(date="2026-06-05")[2], 100)  # only the first issue
		self.assertEqual(self.get_row(date="2026-06-15")[2], 200)  # both issues

	def get_row(self, date, shareholder=None):
		filters = frappe._dict(
			{"date": date, "company": COMPANY, "shareholder": shareholder or self.shareholder}
		)
		data = execute(filters)[1]
		holdings = [r for r in data if r[1] == self.share_type]
		self.assertEqual(len(holdings), 1, f"Expected one row for share type, got: {data}")
		return holdings[0]


def create_share_type(title):
	if not frappe.db.exists("Share Type", title):
		frappe.get_doc({"doctype": "Share Type", "title": title}).insert()
	return title


def create_shareholder(title, company):
	shareholder = frappe.get_doc({"doctype": "Shareholder", "title": title, "company": company}).insert()
	return shareholder.name


def create_share_transfer(**kwargs):
	kwargs.setdefault("company", COMPANY)
	kwargs.setdefault("asset_account", "Cash - _TC")
	kwargs.setdefault("equity_or_liability_account", "Creditors - _TC")
	transfer = frappe.get_doc({"doctype": "Share Transfer", **kwargs})
	transfer.submit()
	return transfer

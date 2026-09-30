# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.trial_balance_for_party.trial_balance_for_party import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestTrialBalanceForParty(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"party_type": "Customer",
				"fiscal_year": "_Test Fiscal Year 2026",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				**extra,
			}
		)
		return execute(filters)[1]

	def party_row(self, party, **extra):
		return next(row for row in self.run_report(party=party, **extra) if row.get("party") == party)

	def test_sales_invoice_shown_as_period_debit(self):
		customer = "_Test Customer"
		create_sales_invoice(customer=customer, qty=1, rate=10000, posting_date="2026-06-01")

		row = self.party_row(customer)
		self.assertEqual(row["opening_debit"], 0)
		self.assertEqual(row["debit"], 10000)
		self.assertEqual(row["credit"], 0)
		self.assertEqual(row["closing_debit"], 10000)
		self.assertEqual(row["closing_credit"], 0)

	def test_receipt_nets_invoice_in_closing(self):
		customer = "_Test Customer"
		create_sales_invoice(customer=customer, qty=1, rate=10000, posting_date="2026-06-01")
		create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party=customer,
			paid_from="Debtors - _TC",
			paid_to="_Test Bank - _TC",
			paid_amount=4000,
			save=True,
			submit=True,
		)

		row = self.party_row(customer)
		self.assertEqual(row["debit"], 10000)
		self.assertEqual(row["credit"], 4000)
		# closing nets debit against credit: 10000 - 4000
		self.assertEqual(row["closing_debit"], 6000)
		self.assertEqual(row["closing_credit"], 0)

	def test_prior_period_invoice_shown_as_opening(self):
		customer = "_Test Customer"
		# invoice dated before from_date should land in the opening balance, not within-period
		create_sales_invoice(customer=customer, qty=1, rate=10000, posting_date="2025-12-01")

		row = self.party_row(customer)
		self.assertEqual(row["opening_debit"], 10000)
		self.assertEqual(row["debit"], 0)
		self.assertEqual(row["closing_debit"], 10000)

	def test_exclude_zero_balance_parties(self):
		customer = "_Test Customer"
		create_sales_invoice(customer=customer, qty=1, rate=10000, posting_date="2026-06-01")
		create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party=customer,
			paid_from="Debtors - _TC",
			paid_to="_Test Bank - _TC",
			paid_amount=10000,
			save=True,
			submit=True,
		)

		# fully settled party still shows by default ...
		self.assertEqual(self.party_row(customer)["closing_debit"], 0)
		# ... but is hidden when zero-balance parties are excluded
		parties = {row.get("party") for row in self.run_report(exclude_zero_balance_parties=1)}
		self.assertNotIn(customer, parties)

	def test_purchase_invoice_shown_as_supplier_credit(self):
		supplier = "_Test Supplier"
		make_purchase_invoice(supplier=supplier, qty=1, rate=8000, posting_date="2026-06-01")

		row = self.party_row(supplier, party_type="Supplier")
		self.assertEqual(row["credit"], 8000)
		self.assertEqual(row["debit"], 0)
		self.assertEqual(row["closing_credit"], 8000)
		self.assertEqual(row["closing_debit"], 0)

	def test_totals_row_sums_party_rows(self):
		create_sales_invoice(customer="_Test Customer 1", qty=1, rate=10000, posting_date="2026-06-01")
		create_sales_invoice(customer="_Test Customer 2", qty=1, rate=6000, posting_date="2026-06-01")

		data = self.run_report()
		totals = data[-1]  # totals row is appended last
		party_rows = data[:-1]
		for column in (
			"opening_debit",
			"opening_credit",
			"debit",
			"credit",
			"closing_debit",
			"closing_credit",
		):
			self.assertEqual(totals[column], sum(row[column] for row in party_rows))

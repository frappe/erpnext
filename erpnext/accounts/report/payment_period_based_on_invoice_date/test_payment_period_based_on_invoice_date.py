# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import getdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.payment_period_based_on_invoice_date.payment_period_based_on_invoice_date import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestPaymentPeriodBasedOnInvoiceDate(ERPNextTestSuite):
	"""Depth tests for the Payment Period Based On Invoice Date report.

	The report lists Payment Ledger Entries against invoices and buckets the paid
	amount by the payment period -- how long after the invoice the payment was made
	(payment date - invoice date) -- into ranges: range1 (0-30), range2 (30-60),
	range3 (60-90), range4 (90 Above).
	"""

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"payment_type": "Incoming",
				"party_type": "Customer",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
			}
		)
		filters.update(extra)
		columns, data = execute(filters)
		fieldnames = [c["fieldname"] for c in columns]
		# Map each positional row to a dict keyed by column fieldname so assertions
		# stay correct even if a column is inserted or reordered.
		return columns, [dict(zip(fieldnames, row, strict=False)) for row in data]

	def find_payment_row(self, data, payment_name):
		for row in data:
			if row["payment_entry"] == payment_name:
				return row
		return None

	def pay_invoice(self, invoice, payment_date):
		pe = get_payment_entry("Sales Invoice", invoice.name)
		pe.posting_date = payment_date
		pe.reference_no = "1"
		pe.reference_date = payment_date
		pe.submit()
		return pe

	def test_paid_amount_lands_in_0_30_bucket(self):
		# invoice 2026-06-01, paid 2026-06-20 -> 19 days after -> 0-30 bucket
		invoice = create_sales_invoice(customer="_Test Customer", rate=1000, posting_date="2026-06-01")
		payment = self.pay_invoice(invoice, "2026-06-20")

		_columns, data = self.run_report()

		row = self.find_payment_row(data, payment.name)
		self.assertIsNotNone(row, "Payment row not found in report output")

		self.assertEqual(row["party_type"], "Customer")
		self.assertEqual(row["posting_date"], getdate("2026-06-20"))
		self.assertEqual(row["invoice"], invoice.name)
		self.assertEqual(row["invoice_posting_date"], getdate("2026-06-01"))
		self.assertEqual(row["amount"], 1000)
		self.assertEqual(row["age"], 19)  # age = payment date - invoice date

		# Buckets: 0-30 filled, others empty.
		self.assertEqual(row["range1"], 1000)  # 0-30
		self.assertEqual(row["range2"], 0)  # 30-60
		self.assertEqual(row["range3"], 0)  # 60-90
		self.assertEqual(row["range4"], 0)  # 90 Above

	def test_paid_amount_lands_in_30_60_bucket(self):
		# invoice 2026-06-01, paid 2026-07-16 -> 45 days after -> 30-60 bucket
		invoice = create_sales_invoice(customer="_Test Customer 1", rate=1000, posting_date="2026-06-01")
		payment = self.pay_invoice(invoice, "2026-07-16")

		_columns, data = self.run_report()

		row = self.find_payment_row(data, payment.name)
		self.assertIsNotNone(row, "Payment row not found in report output")

		self.assertEqual(row["amount"], 1000)
		self.assertEqual(row["age"], 45)
		# Buckets: 30-60 filled, others empty.
		self.assertEqual(row["range1"], 0)
		self.assertEqual(row["range2"], 1000)
		self.assertEqual(row["range3"], 0)
		self.assertEqual(row["range4"], 0)

	def test_payment_over_90_days_lands_in_90_above_bucket(self):
		# invoice 2026-01-01, paid 2026-06-01 -> 151 days after -> "90 Above" bucket.
		# Regression guard: with four range columns, a payment older than the last
		# threshold must fall into range4 rather than an unread range5 (showing 0).
		invoice = create_sales_invoice(customer="_Test Customer 2", rate=1000, posting_date="2026-01-01")
		payment = self.pay_invoice(invoice, "2026-06-01")

		_columns, data = self.run_report()

		row = self.find_payment_row(data, payment.name)
		self.assertIsNotNone(row, "Payment row not found in report output")

		self.assertEqual(row["amount"], 1000)
		self.assertEqual(row["age"], 151)
		self.assertEqual(row["range1"], 0)
		self.assertEqual(row["range2"], 0)
		self.assertEqual(row["range3"], 0)
		self.assertEqual(row["range4"], 1000)  # 90 Above captures the full amount

	def test_columns_expose_expected_age_buckets(self):
		columns, _data = self.run_report()
		labels_by_fieldname = {c["fieldname"]: c["label"] for c in columns}
		self.assertEqual(labels_by_fieldname["range1"], "0-30")
		self.assertEqual(labels_by_fieldname["range2"], "30-60")
		self.assertEqual(labels_by_fieldname["range3"], "60-90")
		self.assertEqual(labels_by_fieldname["range4"], "90 Above")
		# Sales Invoice link for Incoming payments.
		invoice_col = next(c for c in columns if c["fieldname"] == "invoice")
		self.assertEqual(invoice_col["options"], "Sales Invoice")

	def test_invalid_payment_type_party_type_combo_throws(self):
		# Incoming + Supplier is invalid.
		self.assertRaises(
			frappe.ValidationError,
			self.run_report,
			payment_type="Incoming",
			party_type="Supplier",
		)
		# Outgoing + Customer is invalid.
		self.assertRaises(
			frappe.ValidationError,
			self.run_report,
			payment_type="Outgoing",
			party_type="Customer",
		)

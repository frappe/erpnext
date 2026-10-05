# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.invalid_ledger_entries.invalid_ledger_entries import execute


class TestInvalidLedgerEntries(FrappeTestCase):
	"""Tests for the Invalid Ledger Entries integrity report.

	The report flags vouchers that still have *active* ledger entries
	(GL Entry with is_cancelled=0 or Payment Ledger Entry with delinked=0)
	in the given period, but whose source voucher document is no longer
	submitted (docstatus != 1). Such orphaned ledgers indicate corruption.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def setUp(self):
		self.company = "_Test Company"
		self.from_date = "2026-01-01"
		self.to_date = "2026-12-31"
		self.posting_date = "2026-06-01"

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": self.company,
				"from_date": self.from_date,
				"to_date": self.to_date,
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_payment_allocated_to_cancelled_invoice_flagged(self):
		"""A payment's ledger row still allocated to a cancelled invoice flags the invoice."""
		invoice = create_sales_invoice(posting_date=self.posting_date, rate=500)
		payment = get_payment_entry("Sales Invoice", invoice.name)
		payment.posting_date = self.posting_date
		payment.reference_no, payment.reference_date = "ILE-1", self.posting_date
		payment.submit()

		frappe.db.set_value("Sales Invoice", invoice.name, "docstatus", 2, update_modified=False)
		frappe.db.set_value("GL Entry", {"voucher_no": invoice.name}, "is_cancelled", 1)
		frappe.db.set_value("Payment Ledger Entry", {"voucher_no": invoice.name}, "delinked", 1)

		flagged = {row.get("voucher_no") for row in self.run_report()}
		self.assertIn(invoice.name, flagged)
		self.assertNotIn(payment.name, flagged)

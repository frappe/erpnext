# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.accounts_payable_summary.accounts_payable_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountsPayableSummary(ERPNextTestSuite):
	"""Payable Summary is a thin wrapper over AccountsReceivableSummary with
	account_type=Payable; these tests lock the supplier-side output: invoiced,
	advance, paid, outstanding, ageing buckets and the optional GL-balance /
	future-payment columns."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.maxDiff = None
		self.company = "_Test Company"
		self.supplier = "_Test Supplier"

	def _filters(self, **overrides):
		filters = {
			"company": self.company,
			"supplier": self.supplier,
			"posting_date": today(),
			"range": "30, 60, 90, 120",
		}
		filters.update(overrides)
		return filters

	def _make_invoice(self, rate=200):
		return make_purchase_invoice(
			company=self.company,
			supplier=self.supplier,
			qty=1,
			rate=rate,
			price_list_rate=rate,
			posting_date=today(),
		)

	def _expected_row(self, pi, **overrides):
		supplier_group = frappe.db.get_value("Supplier", self.supplier, "supplier_group")
		row = {
			"party_type": "Supplier",
			"advance": 0,
			"party": self.supplier,
			"invoiced": 200.0,
			"paid": 0.0,
			"credit_note": 0.0,
			"outstanding": 200.0,
			"range1": 200.0,
			"range2": 0.0,
			"range3": 0.0,
			"range4": 0.0,
			"range5": 0.0,
			"total_due": 200.0,
			"future_amount": 0.0,
			"sales_person": [],
			"currency": pi.currency,
			"supplier_group": supplier_group,
		}
		row.update(overrides)
		return row

	def test_01_payable_summary_output(self):
		"""Invoiced -> advance -> partial payment progression for a single supplier."""
		filters = self._filters()
		pi = self._make_invoice()

		expected = self._expected_row(pi)
		rows = execute(filters)[1]
		self.assertEqual(len(rows), 1)
		self.assertDictEqual(rows[0], expected)

		# advance payment: pay 50 but allocate nothing against the invoice
		pe = get_payment_entry(pi.doctype, pi.name)
		pe.paid_amount = 50
		pe.references[0].allocated_amount = 0
		pe.save().submit()

		expected.update({"advance": 50.0, "outstanding": 150.0, "range1": 150.0, "total_due": 150.0})
		rows = execute(filters)[1]
		self.assertEqual(len(rows), 1)
		self.assertDictEqual(rows[0], expected)

		# partial payment allocated against the invoice
		pe = get_payment_entry(pi.doctype, pi.name)
		pe.paid_amount = 125
		pe.references[0].allocated_amount = 125
		pe.save().submit()

		expected.update(
			{"advance": 50.0, "paid": 125.0, "outstanding": 25.0, "range1": 25.0, "total_due": 25.0}
		)
		rows = execute(filters)[1]
		self.assertEqual(len(rows), 1)
		self.assertDictEqual(rows[0], expected)

	@ERPNextTestSuite.change_settings("Buying Settings", {"supp_master_name": "Naming Series"})
	def test_02_gl_balance_and_future_payment_columns(self):
		"""Naming-series naming adds party_name; show_gl_balance / show_future_payments
		add their columns; a fully-paid invoice drops out of the report."""
		filters = self._filters()
		pi = self._make_invoice()

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.paid_amount = 150
		pe.references[0].allocated_amount = 150
		pe.save().submit()

		expected = self._expected_row(
			pi,
			party_name=frappe.db.get_value("Supplier", self.supplier, "supplier_name"),
			paid=150.0,
			outstanding=50.0,
			range1=50.0,
			total_due=50.0,
		)
		rows = execute(filters)[1]
		self.assertEqual(len(rows), 1)
		self.assertDictEqual(rows[0], expected)

		# GL balance reconciliation columns
		filters.update({"show_gl_balance": True})
		expected.update({"gl_balance": 50.0, "diff": 0.0})
		rows = execute(filters)[1]
		self.assertEqual(len(rows), 1)
		self.assertDictEqual(rows[0], expected)

		# future payment columns
		filters.update({"show_future_payments": True})
		expected.update({"remaining_balance": 50.0})
		rows = execute(filters)[1]
		self.assertEqual(len(rows), 1)
		self.assertDictEqual(rows[0], expected)

		# clear the remaining balance -> supplier drops out of the summary entirely
		get_payment_entry(pi.doctype, pi.name).save().submit()
		rows = execute(filters)[1]
		self.assertEqual(len(rows), 0)

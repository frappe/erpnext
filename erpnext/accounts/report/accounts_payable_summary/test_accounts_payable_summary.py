# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.accounts_payable_summary.accounts_payable_summary import execute


class TestAccountsPayableSummary(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.maxDiff = None
		self.company = "_Test Company"
		self.supplier = "_Test Supplier"

	def tearDown(self):
		frappe.db.rollback()

	def _filters(self, **overrides):
		filters = {
			"company": self.company,
			"party_type": "Supplier",
			"party": [self.supplier],
			"posting_date": today(),
			"range": "30, 60, 90, 120",
		}
		filters.update(overrides)
		return filters

	def _make_invoice(self, rate=200, due_date=None):
		pi = make_purchase_invoice(
			company=self.company,
			supplier=self.supplier,
			qty=1,
			rate=rate,
			price_list_rate=rate,
			posting_date=today(),
			do_not_save=True,
		)
		pi.due_date = due_date or today()
		pi.insert()
		return pi.submit()

	def _make_journal_entry(self, amount: float, offset_account: str, **supplier_row) -> Document:
		"""Credit the supplier by `amount` (a negative amount debits it) against `offset_account`."""
		je = frappe.new_doc("Journal Entry")
		je.update({"company": self.company, "posting_date": today()})
		je.append(
			"accounts",
			{
				"account": "Creditors - _TC",
				"party_type": "Supplier",
				"party": self.supplier,
				"cost_center": "_Test Cost Center - _TC",
				"credit_in_account_currency": max(amount, 0),
				"debit_in_account_currency": max(-amount, 0),
				**supplier_row,
			},
		)
		je.append(
			"accounts",
			{
				"account": offset_account,
				"cost_center": "_Test Cost Center - _TC",
				"debit_in_account_currency": max(amount, 0),
				"credit_in_account_currency": max(-amount, 0),
			},
		)
		return je.submit()

	def test_gl_balance_ignores_customer_of_same_name(self):
		self._make_invoice()
		if not frappe.db.exists("Customer", self.supplier):
			frappe.get_doc(doctype="Customer", customer_name=self.supplier).insert()
		create_sales_invoice(customer=self.supplier, rate=700)

		row = execute(self._filters(show_gl_balance=True))[1][0]

		self.assertEqual((row.gl_balance, row.diff), (200.0, 0.0))

	def test_advance_follows_cost_center_filter(self):
		for cost_center, amount in (("Main - _TC", 50), ("_Test Cost Center 2 - _TC", 30)):
			pe = create_payment_entry(party=self.supplier, paid_amount=amount)
			pe.cost_center = cost_center
			pe.save().submit()

		row = execute(self._filters(cost_center="Main - _TC"))[1][0]

		self.assertEqual((row.advance, row.paid, row.outstanding), (50.0, 0.0, -50.0))

	def test_payment_against_journal_entry_is_not_advance(self):
		debt = self._make_journal_entry(500, "_Test Account Cost for Goods Sold - _TC")
		self._make_journal_entry(
			-300, "_Test Bank - _TC", reference_type="Journal Entry", reference_name=debt.name
		)
		self._make_journal_entry(-80, "_Test Bank - _TC")

		row = execute(self._filters())[1][0]

		self.assertEqual((row.advance, row.invoiced, row.paid, row.outstanding), (80.0, 500.0, 300.0, 120.0))

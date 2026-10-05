# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.payment_period_based_on_invoice_date.payment_period_based_on_invoice_date import (
	execute,
)


class TestPaymentPeriodBasedOnInvoiceDate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

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
		return columns, [dict(zip(fieldnames, row, strict=False)) for row in data]

	def pay_invoice(self, invoice, payment_date):
		pe = get_payment_entry("Sales Invoice", invoice.name)
		pe.posting_date = payment_date
		pe.reference_no = "1"
		pe.reference_date = payment_date
		pe.submit()
		return pe

	def test_only_payments_are_listed(self):
		invoice = create_sales_invoice(customer="_Test Customer", rate=1000, posting_date="2026-06-01")
		create_sales_invoice(customer="_Test Customer", rate=500, posting_date="2026-06-05")
		create_sales_invoice(
			customer="_Test Customer",
			qty=-1,
			rate=100,
			is_return=1,
			return_against=invoice.name,
			posting_date="2026-06-10",
		)
		payment = self.pay_invoice(invoice, "2026-06-20")

		_columns, data = self.run_report(party="_Test Customer")

		self.assertEqual(
			[(row["payment_entry"], row["amount"]) for row in data], [(payment.name, payment.paid_amount)]
		)

	def test_user_sees_payments_of_permitted_customers_only(self):
		for customer in ("_Test Customer", "_Test Customer 1"):
			invoice = create_sales_invoice(customer=customer, rate=1000, posting_date="2026-06-01")
			self.pay_invoice(invoice, "2026-06-20")
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"{frappe.generate_hash(length=10)}@example.com",
				"first_name": "Payment Period Test",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Customer",
				"for_value": "_Test Customer",
			}
		).insert(ignore_permissions=True)

		frappe.set_user(user.name)
		try:
			_columns, data = self.run_report()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual({row["party"] for row in data}, {"_Test Customer"})


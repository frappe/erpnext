# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.payment_period_based_on_invoice_date.payment_period_based_on_invoice_date import (
	execute,
)

TEST_CUSTOMERS = ("_Test Customer", "_Test Customer 1")


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

	def test_cash_invoice_payments_are_listed(self):
		pos_profile = make_pos_profile()
		invoice = create_sales_invoice(
			customer="_Test Customer", rate=1000, posting_date="2026-06-01", do_not_save=True
		)
		invoice.is_pos = 1
		invoice.pos_profile = pos_profile.name
		invoice.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 1000})
		invoice.submit()

		_columns, data = self.run_report(party="_Test Customer")

		self.assertEqual(
			[(row["payment_entry"], row["invoice"], row["amount"]) for row in data],
			[(invoice.name, invoice.name, 1000)],
		)

	def test_user_sees_payments_of_permitted_customers_only(self):
		self.pay_invoices_of_two_customers()
		user = self.create_user_with_customer_permission("_Test Customer")

		self.assertEqual(self.get_test_parties(self.run_report_as(user)), {"_Test Customer"})

	def test_customer_permission_for_other_doctype_does_not_restrict(self):
		self.pay_invoices_of_two_customers()
		user = self.create_user_with_customer_permission(
			"_Test Customer", apply_to_all_doctypes=0, applicable_for="Sales Invoice"
		)

		self.assertEqual(self.get_test_parties(self.run_report_as(user)), set(TEST_CUSTOMERS))

	def get_test_parties(self, data):
		"""Parties of these tests in the report, ignoring other parties' committed data."""
		return {row["party"] for row in data} & set(TEST_CUSTOMERS)

	def pay_invoices_of_two_customers(self):
		for customer in TEST_CUSTOMERS:
			invoice = create_sales_invoice(customer=customer, rate=1000, posting_date="2026-06-01")
			self.pay_invoice(invoice, "2026-06-20")

	def create_user_with_customer_permission(self, customer, **permission):
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
				"for_value": customer,
				**permission,
			}
		).insert(ignore_permissions=True)
		return user.name

	def run_report_as(self, user):
		frappe.set_user(user)
		try:
			return self.run_report()[1]
		finally:
			frappe.set_user("Administrator")

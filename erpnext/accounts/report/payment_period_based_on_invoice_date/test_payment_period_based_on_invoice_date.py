import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
	create_company,
	create_customer,
	get_or_create_fiscal_year,
	get_payment_entry,
	make_test_item,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

from .payment_period_based_on_invoice_date import execute


class TestPaymentPeriodBasedOnInvoiceDate(FrappeTestCase):
	def setUp(self):
		self.customer = "_Test Customer"
		self.company = "_Test Company"

		create_company()
		create_customer(self.customer, "INR")
		make_test_item("_Test Item")
		get_or_create_fiscal_year(self.company)

		# Create a Sales Invoice
		self.sales_invoice = create_sales_invoice(
			customer=self.customer,
			company=self.company,
			qty=1,
			rate=1000,
		)
		self.sales_invoice.submit()

		# Create a Payment Entry against Sales Invoice
		self.payment_entry = get_payment_entry(self.sales_invoice.doctype, self.sales_invoice.name, 1000)
		self.payment_entry.submit()

	def test_execute_with_valid_filters_TC_ACC_531(self):
		filters = frappe._dict(
			{
				"payment_type": "Incoming",
				"company": self.company,
				"party": self.customer,
				"from_date": self.sales_invoice.posting_date,
				"to_date": self.sales_invoice.posting_date,
			}
		)

		columns, data = execute(filters)

		# Assertions
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)
		self.assertGreater(len(columns), 0, "Report must return columns")
		self.assertGreater(len(data), 0, "Report must return at least one row")

		first_row = data[0]
		self.assertEqual(first_row[2], "Customer")
		self.assertEqual(first_row[3], self.customer)

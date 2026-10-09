# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.report.customers_without_any_sales_transactions.customers_without_any_sales_transactions import (
	execute,
)
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.tests.utils import ERPNextTestSuite


class TestCustomersWithoutAnySalesTransactions(ERPNextTestSuite):
	"""Lists customers with no submitted sales transaction of any type."""

	def make_customer(self, name):
		if not frappe.db.exists("Customer", name):
			customer = frappe.new_doc("Customer")
			customer.customer_name = name
			customer.customer_group = "_Test Customer Group"
			customer.territory = "_Test Territory"
			customer.insert()
		return name

	def customers_in_report(self, **filters):
		return {row["customer"] for row in execute(frappe._dict(filters))[1]}

	def test_customer_with_no_transactions_is_listed(self):
		customer = self.make_customer("_Test CWST No Txn")
		self.assertIn(customer, self.customers_in_report())

	def test_delivery_only_customer_is_excluded(self):
		customer = self.make_customer("_Test CWST Delivery Only")
		create_delivery_note(customer=customer)  # submitted, no invoice or order
		self.assertNotIn(customer, self.customers_in_report())

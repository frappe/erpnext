# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.inactive_customers.inactive_customers import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestInactiveCustomers(ERPNextTestSuite):
	def setUp(self):
		self.customer = frappe.get_doc(doctype="Customer", customer_name="_Test Inactive Customer").insert()
		self.last_order_date = add_days(today(), -120)
		so = make_sales_order(
			customer=self.customer.name,
			transaction_date=self.last_order_date,
			qty=5,
			rate=200,
		)
		so.submit()
		self.sales_order = so

	def test_invalid_doctype_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			{"doctype": "Purchase Order", "days_since_last_order": 30},
		)

	def test_inactive_customer_is_listed_with_expected_columns(self):
		columns, data = execute({"doctype": "Sales Order", "days_since_last_order": 30})

		row = self.get_customer_row(data)
		self.assertIsNotNone(row, "Inactive customer should be present in the report")

		# Column contract: the report relies on positional access.
		self.assertEqual(row[0], self.customer.name)
		self.assertEqual(row[7], 1000)  # Last Order Amount inserted at index 7 (5 * 200)
		self.assertEqual(getdate(row[8]), getdate(self.last_order_date))  # Last Order Date
		self.assertGreaterEqual(row[9], 30)  # Days Since Last Order

	def test_recent_customer_is_excluded(self):
		_columns, data = execute({"doctype": "Sales Order", "days_since_last_order": 200})
		self.assertIsNone(
			self.get_customer_row(data),
			"Customer ordering within the threshold must be excluded",
		)

	def get_customer_row(self, data):
		return next((row for row in data if row[0] == self.customer.name), None)

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

	def get_customer_row(self, data, customer=None):
		customer = customer or self.customer.name
		return next((row for row in data if row.customer == customer), None)

	def test_invalid_doctype_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			{"doctype": "Purchase Order", "days_since_last_order": 30},
		)

	def test_inactive_customer_is_listed_with_expected_values(self):
		_columns, data = execute({"doctype": "Sales Order", "days_since_last_order": 30})

		row = self.get_customer_row(data)
		self.assertIsNotNone(row, "Inactive customer should be present in the report")
		self.assertEqual(row.num_of_order, 1)
		self.assertEqual(row.last_order_amount, 1000)  # 5 * 200
		self.assertEqual(getdate(row.last_order_date), getdate(self.last_order_date))
		self.assertGreaterEqual(row.days_since_last_order, 30)

	def test_recent_customer_is_excluded(self):
		_columns, data = execute({"doctype": "Sales Order", "days_since_last_order": 200})
		self.assertIsNone(
			self.get_customer_row(data),
			"Customer ordering within the threshold must be excluded",
		)

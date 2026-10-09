# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
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

	def make_territory(self, name):
		if not frappe.db.exists("Territory", name):
			frappe.get_doc(
				doctype="Territory", territory_name=name, parent_territory="All Territories", is_group=0
			).insert()
		return name

	def test_invalid_doctype_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			{"doctype": "Purchase Order", "days_since_last_order": 30},
		)

	def test_zero_days_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			{"doctype": "Sales Order", "days_since_last_order": 0},
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

	def test_closed_order_considered_pro_rata(self):
		frappe.db.set_value("Sales Order", self.sales_order.name, {"status": "Closed", "per_delivered": 50})
		_columns, data = execute({"doctype": "Sales Order", "days_since_last_order": 30})

		row = self.get_customer_row(data)
		self.assertEqual(row.total_order_value, 1000)
		self.assertEqual(row.total_order_considered, 500)

	def test_credit_note_does_not_reset_recency(self):
		customer = frappe.get_doc(doctype="Customer", customer_name="_Test Inactive SI Customer").insert()
		invoice = create_sales_invoice(
			customer=customer.name, posting_date=self.last_order_date, qty=1, rate=1000
		)
		create_sales_invoice(
			customer=customer.name,
			posting_date=today(),
			qty=-1,
			rate=1000,
			is_return=1,
			return_against=invoice.name,
		)

		_columns, data = execute({"doctype": "Sales Invoice", "days_since_last_order": 30})
		row = self.get_customer_row(data, customer.name)

		self.assertIsNotNone(row, "Credit note must not drop the customer from the inactive list")
		self.assertEqual(row.num_of_order, 1)  # the return is not an order
		self.assertEqual(row.last_order_amount, 1000)  # not the -1000 credit note
		self.assertEqual(getdate(row.last_order_date), getdate(self.last_order_date))

	def test_territory_user_permission_restricts_customers(self):
		self.make_territory("_Test Inactive Territory A")
		self.make_territory("_Test Inactive Territory B")
		visible = frappe.get_doc(
			doctype="Customer",
			customer_name="_Test Inactive In Territory",
			territory="_Test Inactive Territory A",
		).insert()
		hidden = frappe.get_doc(
			doctype="Customer",
			customer_name="_Test Inactive Other Territory",
			territory="_Test Inactive Territory B",
		).insert()
		for cust in (visible.name, hidden.name):
			make_sales_order(customer=cust, transaction_date=self.last_order_date, qty=1, rate=100).submit()

		user = "_test_inactive_territory@example.com"
		if not frappe.db.exists("User", user):
			restricted = frappe.new_doc("User")
			restricted.email = user
			restricted.first_name = "Inactive Territory"
			restricted.append("roles", {"role": "Sales User"})
			restricted.insert()
		frappe.permissions.add_user_permission("Territory", "_Test Inactive Territory A", user)

		frappe.set_user(user)
		try:
			_columns, data = execute({"doctype": "Sales Order", "days_since_last_order": 30})
			listed = {row.customer for row in data}
		finally:
			frappe.set_user("Administrator")

		self.assertIn(visible.name, listed)
		self.assertNotIn(hidden.name, listed)

# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import random_string

from erpnext.selling.report.customer_credit_balance.customer_credit_balance import (
	execute,
	get_columns,
	get_details,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestCustomerCreditBalance(ERPNextTestSuite):
	def test_get_details_returns_customer_with_credit_limit(self):
		company = "_Test Company"
		customer_name = "_Test Credit Balance " + random_string(8)

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
				"credit_limits": [
					{
						"company": company,
						"credit_limit": 50000,
						"bypass_credit_limit_check": 1,
					}
				],
			}
		).insert()

		rows = get_details(frappe._dict(company=company, customer=customer.name))

		# Inner join + company + customer filters must isolate exactly this customer's row.
		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertEqual(row.name, customer.name)
		self.assertEqual(row.customer_name, customer_name)
		self.assertEqual(row.bypass_credit_limit_check, 1)

	def test_get_details_excludes_other_company_credit_limit(self):
		# Credit limit child row exists, but for a different company than the filter,
		# so the company-filtered inner join must return nothing for this customer.
		company = "_Test Company"
		customer_name = "_Test Credit Balance " + random_string(8)

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
				"credit_limits": [
					{
						"company": "_Test Company 1",
						"credit_limit": 50000,
						"bypass_credit_limit_check": 0,
					}
				],
			}
		).insert()

		rows = get_details(frappe._dict(company=company, customer=customer.name))
		self.assertEqual(len(rows), 0)

	def test_get_details_lists_customer_with_group_level_limit(self):
		# limit on the group (not the customer) must still list the customer
		company = "_Test Company"
		group_name = "_Test Credit Group " + random_string(8)

		group = frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": group_name,
				"parent_customer_group": "All Customer Groups",
				"credit_limits": [{"company": company, "credit_limit": 50000}],
			}
		).insert()

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Credit Balance " + random_string(8),
				"customer_group": group.name,
				"territory": "_Test Territory",
			}
		).insert()

		rows = get_details(frappe._dict(company=company, customer=customer.name))
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].name, customer.name)

	def test_get_details_lists_customer_with_company_wide_limit(self):
		# a company-wide limit (no customer or group limit) must still list the customer
		company = "_Test Company"
		frappe.db.set_value("Company", company, "credit_limit", 20000)
		self.addCleanup(frappe.db.set_value, "Company", company, "credit_limit", 0)

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Credit Balance " + random_string(8),
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		).insert()

		rows = get_details(frappe._dict(company=company, customer=customer.name))
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].name, customer.name)

	def test_breakup_columns_only_when_requested(self):
		without_breakup = get_columns("Customer Name")
		with_breakup = get_columns("Customer Name", show_breakup=True)

		self.assertEqual(len(with_breakup), len(without_breakup) + 3)
		self.assertTrue(any("Pending Sales Orders" in col for col in with_breakup))
		self.assertFalse(any("Pending Sales Orders" in col for col in without_breakup))

	def test_execute_breakup_values_and_positions(self):
		company = "_Test Company"
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Credit Balance " + random_string(8),
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
				"credit_limits": [{"company": company, "credit_limit": 1000}],
			}
		).insert()
		breakup = frappe._dict(gle=100.0, sales_order=200.0, delivery_note=50.0)
		filters = frappe._dict(company=company, customer=customer.name)
		module = "erpnext.selling.report.customer_credit_balance.customer_credit_balance"

		for naming_type, offset in (("Customer Name", 0), ("Naming Series", 1)):
			frappe.db.set_single_value("Selling Settings", "cust_master_name", naming_type)
			with patch(f"{module}.get_customer_outstanding_breakup", return_value=breakup):
				columns, data = execute(filters)
				breakup_columns, breakup_data = execute(frappe._dict(filters, show_breakup=1))

			self.assertEqual(len(columns), len(data[0]))
			self.assertEqual(len(breakup_columns), len(breakup_data[0]))

			# without breakup: customer, [customer name], credit limit, outstanding, balance
			row = data[0]
			self.assertEqual(row[0], customer.name)
			self.assertEqual(row[1 + offset], 1000)
			self.assertEqual(row[2 + offset], 350)
			self.assertEqual(row[3 + offset], 650)

			# with breakup: credit limit, GL, sales order, delivery note, outstanding, balance
			row = breakup_data[0]
			self.assertEqual(row[1 + offset], 1000)
			self.assertEqual(row[2 + offset : 5 + offset], [100.0, 200.0, 50.0])
			self.assertEqual(sum(row[2 + offset : 5 + offset]), row[5 + offset])
			self.assertEqual(row[6 + offset], 650)

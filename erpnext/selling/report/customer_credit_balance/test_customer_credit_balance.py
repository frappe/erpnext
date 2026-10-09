# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from erpnext.selling.report.customer_credit_balance.customer_credit_balance import get_details


class TestCustomerCreditBalance(FrappeTestCase):
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

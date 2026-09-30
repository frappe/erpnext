# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import random_string

from erpnext.selling.report.customer_credit_balance.customer_credit_balance import get_details
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

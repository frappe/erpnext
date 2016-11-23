# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

test_ignore = ["Account", "Cost Center"]

import frappe
import unittest

test_records = frappe.get_test_records('Company')

class TestCompany(unittest.TestCase):
	def test_coa_based_on_existing_company(self):
		make_company()
		
		expected_results = {
			"Debtors - CFEC": {
				"account_type": "Receivable",
				"is_group": 0,
				"root_type": "Asset",
				"parent_account": "Accounts Receivable - CFEC",
			},
			"_Test Cash - CFEC": {
				"account_type": "Cash",
				"is_group": 0,
				"root_type": "Asset",
				"parent_account": "Cash In Hand - CFEC"
			}
		}
		
		for account, acc_property in expected_results.items():
			acc = frappe.get_doc("Account", account)
			for prop, val in acc_property.items():
				self.assertEqual(acc.get(prop), val)
		
		
def make_company():
	company = frappe.new_doc("Company")
	company.company_name = "COA from Existing Company"
	company.abbr = "CFEC"
	company.default_currency = "INR"
	company.create_chart_of_accounts_based_on = "Existing Company"
	company.existing_company = "_Test Company"
	company.save()



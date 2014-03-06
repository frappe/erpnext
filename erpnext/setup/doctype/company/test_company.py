# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

test_ignore = ["Account", "Cost Center"]

import frappe
import unittest

class TestCompany(unittest.TestCase):
	def test_coa(self):
		company_bean = frappe.bean({
			"doctype": "Company",
			"company_name": "_Test Company 2",
			"abbr": "_TC2",
			"default_currency": "INR",
			"country": "India",
			"chart_of_accounts": "India - Chart of Accounts for Public Ltd"
		})

		company_bean.insert()
		
		self.assertTrue(frappe.db.get_value("Account", "Balance Sheet - _TC2"))
		

test_records = [
	[{
		"doctype": "Company",
		"company_name": "_Test Company",
		"abbr": "_TC",
		"default_currency": "INR",
		"domain": "Manufacturing"
	}],
	[{
		"doctype": "Company",
		"company_name": "_Test Company 1",
		"abbr": "_TC1",
		"default_currency": "USD",
		"domain": "Retail"
	}],
]
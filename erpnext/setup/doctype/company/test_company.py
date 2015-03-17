# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

test_ignore = ["Account", "Cost Center"]

import frappe
import unittest

class TestCompany(unittest.TestCase):
	def atest_coa(self):
		for country, chart_name in frappe.db.sql("""select country, chart_name
			from `tabChart of Accounts` where name = 'Deutscher Kontenplan SKR03'""", as_list=1):
				company_doc = frappe.get_doc({
					"doctype": "Company",
					"company_name": "_Test Company 2",
					"abbr": "_TC2",
					"default_currency": "INR",
					"country": country,
					"chart_of_accounts": chart_name
				})

				company_doc.insert()
				self.assertTrue(frappe.db.sql("""select count(*) from tabAccount
					where company='_Test Company 2'""")[0][0] > 10)

				frappe.delete_doc("Company", "_Test Company 2")


test_records = frappe.get_test_records('Company')

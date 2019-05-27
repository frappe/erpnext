# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import random_string
from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import get_charts_for_country

test_ignore = ["Account", "Cost Center", "Payment Terms Template", "Salary Component"]
test_dependencies = ["Fiscal Year"]
test_records = frappe.get_test_records('Company')

class TestCompany(unittest.TestCase):
	def test_coa_based_on_existing_company(self):
		company = frappe.new_doc("Company")
		company.company_name = "COA from Existing Company"
		company.abbr = "CFEC"
		company.default_currency = "INR"
		company.create_chart_of_accounts_based_on = "Existing Company"
		company.existing_company = "_Test Company"
		company.save()
		
		expected_results = {
			"Debtors - CFEC": {
				"account_type": "Receivable",
				"is_group": 0,
				"root_type": "Asset",
				"parent_account": "Accounts Receivable - CFEC",
			},
			"Cash - CFEC": {
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

		self.delete_mode_of_payment("COA from Existing Company")
		frappe.delete_doc("Company", "COA from Existing Company")

	def test_coa_based_on_country_template(self):
		countries = ["India", "Brazil", "United Arab Emirates", "Canada", "Germany", "France",
			"Guatemala", "Indonesia", "Italy", "Mexico", "Nicaragua", "Netherlands", "Singapore",
			"Brazil", "Argentina", "Hungary", "Taiwan"]
		
		for country in countries:
			templates = get_charts_for_country(country)
			if len(templates) != 1 and "Standard" in templates:
				templates.remove("Standard")
			
			self.assertTrue(templates)
			
			for template in templates:
				try:
					company = frappe.new_doc("Company")
					company.company_name = template
					company.abbr = random_string(3)
					company.default_currency = "USD"
					company.create_chart_of_accounts_based_on = "Standard Template"
					company.chart_of_accounts = template
					company.save()
				
					account_types = ["Cost of Goods Sold", "Depreciation", 
						"Expenses Included In Valuation", "Fixed Asset", "Payable", "Receivable", 
						"Stock Adjustment", "Stock Received But Not Billed", "Bank", "Cash", "Stock"]
				
					for account_type in account_types:
						filters = {
							"company": template,
							"account_type": account_type
						}
						if account_type in ["Bank", "Cash"]:
							filters["is_group"] = 1

						self.assertTrue(frappe.get_all("Account", filters))
				finally:
					self.delete_mode_of_payment(template)
					frappe.delete_doc("Company", template)

	def delete_mode_of_payment(self, company):
		frappe.db.sql(""" delete from `tabMode of Payment Account`
			where company =%s """, (company))

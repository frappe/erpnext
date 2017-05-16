import unittest

import frappe
from erpnext import encode_company_abbr
import six.moves.range

test_records = frappe.get_test_records('Company')


class TestInit(unittest.TestCase):
	def setUp(self):
		self.company = frappe.new_doc("Company")
		self.company.company_name = "COA from Existing Company"
		self.company.abbr = "CFEC"
		self.company.default_currency = "INR"
		self.company.create_chart_of_accounts_based_on = "Existing Company"
		self.company.existing_company = "_Test Company"
		self.company.save()

	def test_encode_company_abbr(self):
		abbr = self.company.abbr
		names = [
			"Warehouse Name", "ERPNext Foundation India", "Gold - Member - {a}".format(a=abbr),
		    " - {a}".format(a=abbr), "ERPNext - Foundation - India",
		    "ERPNext Foundation India - {a}".format(a=abbr),
		    "No-Space-{a}".format(a=abbr), "- Warehouse"
		]

		expected_names = [
			"Warehouse Name - {a}".format(a=abbr), "ERPNext Foundation India - {a}".format(a=abbr),
			"Gold - Member - {a}".format(a=abbr), " - {a}".format(a=abbr),
			"ERPNext - Foundation - India - {a}".format(a=abbr),
			"ERPNext Foundation India - {a}".format(a=abbr), "No-Space-{a} - {a}".format(a=self.company.abbr),
			"- Warehouse - {a}".format(a=abbr)
		]

		for i in range(len(names)):
			enc_name = encode_company_abbr(names[i], self.company)
			self.assertTrue(
				enc_name == expected_names[i],
			    "{enc} is not same as {exp}".format(enc=enc_name, exp=expected_names[i])
			)
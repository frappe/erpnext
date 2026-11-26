# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from urllib.parse import parse_qs, urlsplit

import frappe
from bs4 import BeautifulSoup

from erpnext.tests.utils import ERPNextTestSuite


class TestSalesPerson(ERPNextTestSuite):
	def test_disable_error_links_customers_by_encoded_name(self):
		name = 'Quoted SP" class="spinner-border" onanimationstart="alert(1)'
		sales_person = frappe.get_doc(doctype="Sales Person", sales_person_name=name).insert()
		frappe.get_doc(
			doctype="Customer",
			customer_name="Sales Person Link Customer",
			customer_group="_Test Customer Group",
			territory="_Test Territory",
			sales_team=[{"sales_person": sales_person.name, "allocated_percentage": 100}],
		).insert()

		sales_person.enabled = 0
		with self.assertRaises(frappe.ValidationError) as error:
			sales_person.save()

		link = BeautifulSoup(str(error.exception), "html.parser").find("a")
		self.assertEqual(list(link.attrs), ["href"])
		self.assertEqual(parse_qs(urlsplit(link["href"]).query), {"sales_person": [name]})

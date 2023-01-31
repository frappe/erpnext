# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from bs4 import BeautifulSoup
from frappe.utils import set_request
from frappe.website.serve import get_response


class TestHomepageSection(unittest.TestCase):
	def test_homepage_section_custom_html(self):
		frappe.get_doc(
			{
				"doctype": "Homepage Section",
				"name": "Custom HTML Section",
				"section_based_on": "Custom HTML",
				"section_html": '<div class="custom-section">My custom html</div>',
			}
		).insert()

		set_request(method="GET", path="home")
		response = get_response()

		self.assertEqual(response.status_code, 200)

		html = frappe.safe_decode(response.get_data())

		soup = BeautifulSoup(html, "html.parser")
		sections = soup.find("main").find_all(class_="custom-section")
		self.assertEqual(len(sections), 1)

		homepage_section = sections[0]
		self.assertEqual(homepage_section.text, "My custom html")

		# cleanup
		frappe.db.rollback()

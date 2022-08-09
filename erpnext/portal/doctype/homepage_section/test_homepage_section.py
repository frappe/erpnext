# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from bs4 import BeautifulSoup
from frappe.utils import set_request
from frappe.website.serve import get_response


class TestHomepageSection(unittest.TestCase):
	def test_homepage_section_card(self):
		try:
			frappe.get_doc(
				{
					"doctype": "Homepage Section",
					"name": "Card Section",
					"section_based_on": "Cards",
					"section_cards": [
						{
							"title": "Card 1",
							"subtitle": "Subtitle 1",
							"content": "This is test card 1",
							"route": "/card-1",
						},
						{
							"title": "Card 2",
							"subtitle": "Subtitle 2",
							"content": "This is test card 2",
							"image": "test.jpg",
						},
					],
					"no_of_columns": 3,
				}
			).insert(ignore_if_duplicate=True)
		except frappe.DuplicateEntryError:
			pass

		set_request(method="GET", path="home")
		response = get_response()

		self.assertEqual(response.status_code, 200)

		html = frappe.safe_decode(response.get_data())

		soup = BeautifulSoup(html, "html.parser")
		sections = soup.find("main").find_all("section")
		self.assertEqual(len(sections), 3)

		homepage_section = sections[2]
		self.assertEqual(homepage_section.h3.text, "Card Section")

		cards = homepage_section.find_all(class_="card")

		self.assertEqual(len(cards), 2)
		self.assertEqual(cards[0].h5.text, "Card 1")
		self.assertEqual(cards[0].a["href"], "/card-1")
		self.assertEqual(cards[1].p.text, "Subtitle 2")

		img = cards[1].find(class_="card-img-top")

		self.assertEqual(img["src"], "test.jpg")
		self.assertEqual(img["loading"], "lazy")

		# cleanup
		frappe.db.rollback()

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

# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import set_request
from bs4 import BeautifulSoup
from frappe.website.render import render

class TestHomepage(unittest.TestCase):
	def setup_test_data(self):
		try:
			frappe.get_doc({
				'doctype': 'Web Page Card',
				'title': 'Card 1',
				'subtitle': 'Subtitle 1',
				'content': 'This is test card 1',
				'route': '/card-1',
				'route_follow': 0
			}).insert()
		except frappe.DuplicateEntryError:
			pass

		try:
			frappe.get_doc({
				'doctype': 'Web Page Card',
				'title': 'Card 2',
				'subtitle': 'Subtitle 2',
				'content': 'This is test card 2',
				'image': 'test.jpg',
				'route_follow': 1
			}).insert()
		except frappe.DuplicateEntryError:
			pass

		try:
			frappe.get_doc({
				'doctype': 'Web Page Section',
				'name': 'Test Card Section',
				'section_based_on': 'Grid',
				'items': [
					{'content_doctype': 'Web Page Card', 'content_document': 'Card 1', 'render_as': 'Vertical Card', 'route_text': 'Test Card1'},
					{'content_doctype': 'Web Page Card', 'content_document': 'Card 2', 'render_as': 'Horizontal Card', 'route_text': 'Test Card2'},
				],
				'no_of_columns': 3
			}).insert()
		except frappe.DuplicateEntryError:
			pass

		try:
			frappe.get_doc({
				'doctype': 'Web Page Section',
				'name': 'Custom HTML Section',
				'section_based_on': 'Custom HTML',
				'section_html': '<section><div class="custom-section">My custom html</div></section>',
			}).insert()
		except frappe.DuplicateEntryError:
			pass

		try:
			doc = frappe.get_doc('Homepage')
			doc.update({
				'title': 'Test Website',
				'description': 'This is a test website description',
				'hero_section_based_on': 'Default',
				'tag_line': 'Test tagline',
				'hero_image': 'hero.jpg',
				'page_sections': [
					{'section_name': 'Test Card Section', 'is_important': 1},
					{'section_name': 'Custom HTML Section', 'is_important': 0},
				]
			}).save()
		except frappe.DuplicateEntryError:
			pass

	def test_homepage_load(self):
		self.setup_test_data()

		set_request(method='GET', path='home')
		response = render()

		self.assertEquals(response.status_code, 200)

		html = frappe.safe_decode(response.get_data())

		self.assertTrue('<section class="hero-section' in html)

		soup = BeautifulSoup(html, 'html.parser')
		sections = soup.find('main').find_all('section')
		self.assertEqual(len(sections), 3)

		homepage_section = sections[1]
		self.assertEqual(homepage_section.h1.text, 'Test Card Section')

		cards = homepage_section.find_all(class_="card")

		self.assertEqual(len(cards), 2)
		self.assertEqual(cards[0].h3.text.strip(), 'Card 1')
		self.assertEqual(cards[0].a['href'], '/card-1')
		self.assertEqual(cards[1].h4.text, 'Subtitle 2')
		self.assertEqual(cards[1].find(class_='website-image-lazy')['data-src'], 'test.jpg')

		# cleanup
		frappe.db.rollback()

	def test_homepage_section_custom_html(self):
		self.setup_test_data()

		set_request(method='GET', path='home')
		response = render()

		self.assertEquals(response.status_code, 200)

		html = frappe.safe_decode(response.get_data())

		soup = BeautifulSoup(html, 'html.parser')
		sections = soup.find('main').find_all(class_='custom-section')
		self.assertEqual(len(sections), 1)

		html_section = sections[0]
		self.assertEqual(html_section.text, 'My custom html')

		# cleanup
		frappe.db.rollback()

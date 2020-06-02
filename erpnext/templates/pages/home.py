# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.html_utils import clean_html

no_cache = 1


def get_context(context):
	homepage = frappe.get_doc('Homepage')

	homepage.title = homepage.title or homepage.company
	context.title = homepage.title
	context.homepage = homepage

	if homepage.hero_section_based_on == 'Web Page Section' and homepage.hero_section:
		context.hero_section_doc = frappe.get_doc('Web Page Section', homepage.hero_section).map_to_cards()

	if homepage.slideshow:
		doc = frappe.get_doc('Website Slideshow', homepage.slideshow)
		context.slideshow = homepage.slideshow
		context.slideshow_header = doc.header
		context.slides = doc.slideshow_items

	# Build the sections
	context.homepage_sections = []
	for section in homepage.page_sections:
		if not (homepage.hero_section_based_on == 'Web Page Section' and section.section_name == homepage.hero_section):
			wp_section = frappe.get_doc('Web Page Section', section.section_name)
			section.update(wp_section.map_to_cards().__dict__)
			context.homepage_sections += [section]

	context.metatags = context.metatags or frappe._dict({})
	context.metatags.image = homepage.hero_image or None
	context.metatags.description = homepage.description or None

	context.explore_link = '/all-products'

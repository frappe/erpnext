from __future__ import unicode_literals
from unittest import TestCase

import frappe
from erpnext.regional.address_template.setup import get_address_templates
from erpnext.regional.address_template.setup import update_address_template

class TestRegionalAddressTemplate(TestCase):
	def test_get_address_templates(self):
		templates = get_address_templates()
		self.assertIsInstance(templates, list)
		self.assertIsInstance(templates[0], dict)

	def test_update_address_template(self):
		template = "TEST {{ address_line1 }}"
		update_address_template("Test Regional", template)
		doc = frappe.get_doc("Address Template", "Test Regional")
		self.assertEqual(template, doc.template)

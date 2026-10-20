# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestShareClass(IntegrationTestCase):
	def test_class_code_is_unique(self):
		self.make_class().insert()
		with self.assertRaises(frappe.UniqueValidationError):
			self.make_class().insert()

	def make_class(self, **values):
		return frappe.get_doc(
			{
				"doctype": "Share Class",
				"class_name": "Test Class Terms",
				"class_code": self._testMethodName,
				"category": "Ordinary",
				"has_dividend_rights": 0,
				**values,
			}
		)

import unittest

import frappe

import erpnext


@erpnext.allow_regional
def test_method():
	return "original"


class TestInit(unittest.TestCase):
	def test_regional_overrides(self):
		frappe.flags.country = "India"
		self.assertEqual(test_method(), "overridden")

		frappe.flags.country = "Maldives"
		self.assertEqual(test_method(), "original")

		frappe.flags.country = "France"
		self.assertEqual(test_method(), "overridden")

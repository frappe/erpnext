import unittest

import frappe

import erpnext


@erpnext.allow_regional
def test_method():
	return "original"


class TestInit(unittest.TestCase):
	def test_regional_overrides(self):
		frappe.flags.country = "Maldives"
		self.assertEqual(test_method(), "original")

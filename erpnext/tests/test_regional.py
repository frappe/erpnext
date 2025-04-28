import unittest

import frappe
<<<<<<< HEAD
from frappe.tests import IntegrationTestCase
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)

import erpnext


@erpnext.allow_regional
def test_method():
	return "original"


<<<<<<< HEAD
class TestInit(IntegrationTestCase):
=======
class TestInit(unittest.TestCase):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	def test_regional_overrides(self):
		frappe.flags.country = "Maldives"
		self.assertEqual(test_method(), "original")

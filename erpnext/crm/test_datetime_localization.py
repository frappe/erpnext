import unittest
import frappe
from frappe.utils import getdate
from erpnext.crm.utils import get_localized_date


class TestDatetimeLocalization(unittest.TestCase):
	"""Test cases for datetime localization in CRM."""

	def setUp(self):
		"""Set up test case."""
		# Store original language
		self.original_lang = frappe.local.lang
		
	def tearDown(self):
		"""Tear down test case."""
		# Restore original language
		frappe.local.lang = self.original_lang
		
	def test_get_localized_date_with_valid_date(self):
		"""Test get_localized_date with a valid date."""
		# Set language to German for testing
		frappe.local.lang = "de"
		
		test_date = "2023-12-25"
		result = get_localized_date(test_date)
		
		# Should return a string representation of the date
		self.assertIsInstance(result, str)
		self.assertTrue(len(result) > 0)
		
	def test_get_localized_date_with_none(self):
		"""Test get_localized_date with None."""
		result = get_localized_date(None)
		self.assertEqual(result, "")
		
	def test_get_localized_date_with_empty_string(self):
		"""Test get_localized_date with empty string."""
		result = get_localized_date("")
		self.assertEqual(result, "")
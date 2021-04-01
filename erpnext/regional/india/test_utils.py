from __future__ import unicode_literals

import unittest
import frappe
from unittest.mock import patch
from erpnext.regional.india.utils import validate_document_name


class TestIndiaUtils(unittest.TestCase):
	@patch("frappe.get_cached_value")
	def test_validate_document_name(self, mock_get_cached):
		mock_get_cached.return_value = "India"  # mock country
		posting_date = "2021-05-01"

		invalid_names = ["SI$1231", "012345678901234567", "SI 2020 05",
				"SI.2020.0001", "PI2021 - 001"]
		for name in invalid_names:
			doc = frappe._dict(name=name, posting_date=posting_date)
			self.assertRaises(frappe.ValidationError, validate_document_name, doc)

		valid_names = ["012345678901236", "SI/2020/0001", "SI/2020-0001",
			"2020-PI-0001", "PI2020-0001"]
		for name in valid_names:
			doc = frappe._dict(name=name, posting_date=posting_date)
			try:
				validate_document_name(doc)
			except frappe.ValidationError:
				self.fail("Valid name {} throwing error".format(name))

	@patch("frappe.get_cached_value")
	def test_validate_document_name_not_india(self, mock_get_cached):
		mock_get_cached.return_value = "Not India"
		doc = frappe._dict(name="SI$123", posting_date="2021-05-01")

		try:
			validate_document_name(doc)
		except frappe.ValidationError:
			self.fail("Regional validation related to India are being applied to other countries")

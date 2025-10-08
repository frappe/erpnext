# Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.currency_exchange_settings.currency_exchange_settings import (
	get_api_endpoint,
)


class TestCurrencyExchangeSettings(unittest.TestCase):
	def setUp(self):
		frappe.flags.in_test = True

	def tearDown(self):
		frappe.flags.in_test = False

	def test_get_api_endpoint_TC_ACC_298(self):
		endpoint = get_api_endpoint("frankfurter.app", use_http=True)
		self.assertEqual(endpoint, "http://api.frankfurter.app/{transaction_date}")

	# frankfurter
	def test_set_parameters_and_result_TC_ACC_299(self):
		doc = frappe.new_doc("Currency Exchange Settings")
		doc.service_provider = "frankfurter.app"

		doc.set_parameters_and_result()

		self.assertEqual(doc.api_endpoint, "https://api.frankfurter.app/{transaction_date}")
		keys = [row.key for row in doc.req_params]
		self.assertIn("base", keys)
		self.assertIn("symbols", keys)

		result_keys = [row.key for row in doc.result_key]
		self.assertEqual(result_keys, ["rates", "{to_currency}"])

		doc = frappe.new_doc("Currency Exchange Settings")
		doc.service_provider = "exchangerate.host"
		doc.access_key = None

		with self.assertRaises(frappe.ValidationError) as context:
			doc.set_parameters_and_result()

		self.assertIn("Access Key is required", str(context.exception))

	# allow validate API Call
	@patch("erpnext.accounts.doctype.currency_exchange_settings.currency_exchange_settings.requests.get")
	def test_validate_TC_ACC_300(self, mock_get):
		mock_response = unittest.mock.Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"result": 83.42}
		mock_response.text = '{"result": 83.42}'
		mock_response.url = "https://example.com"
		mock_get.return_value = mock_response

		doc = frappe.new_doc("Currency Exchange Settings")
		doc.service_provider = "exchangerate.host"
		doc.access_key = "abc123"
		doc.set_parameters_and_result()

		frappe.flags.in_test = False
		doc.validate()
		self.assertEqual(doc.url, "https://example.com")

	@patch("erpnext.accounts.doctype.currency_exchange_settings.currency_exchange_settings.requests.get")
	def test_validate_result_wrong_type_TC_ACC_301(self, mock_get):
		# Valid Responce
		mock_response = unittest.mock.Mock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"result": "not-a-number"}
		mock_response.text = '{"result": "not-a-number"}'
		mock_response.url = "https://example.com"
		mock_get.return_value = mock_response

		doc = frappe.new_doc("Currency Exchange Settings")
		doc.service_provider = "exchangerate.host"
		doc.access_key = "abc123"
		doc.set_parameters_and_result()

		frappe.flags.in_test = False
		with self.assertRaises(frappe.ValidationError) as context:
			doc.validate()

		self.assertIn("Returned exchange rate is neither integer", str(context.exception))

		# Invalid Key
		mock_response.json.return_value = {"invalid_key": 123}
		mock_response.text = '{"invalid_key": 123}'
		doc.set_parameters_and_result()
		doc.result_key[0].key = "nonexistent_key"

		frappe.flags.in_test = False
		with self.assertRaises(frappe.ValidationError) as context:
			doc.validate()

		self.assertIn("Invalid result key", str(context.exception))

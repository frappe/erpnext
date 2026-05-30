# Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import socket
from unittest.mock import patch

import frappe
from frappe.exceptions import ValidationError

from erpnext.setup.utils import validate_exchange_endpoint
from erpnext.tests.utils import ERPNextTestSuite


class TestCurrencyExchangeSettings(ERPNextTestSuite):
	def test_blocks_loopback_ip(self):
		self.assertRaises(ValidationError, validate_exchange_endpoint, "http://127.0.0.1/api")

	def test_blocks_link_local_ip(self):
		self.assertRaises(
			ValidationError, validate_exchange_endpoint, "http://169.254.169.254/latest/meta-data/"
		)

	def test_blocks_rfc1918_ip(self):
		self.assertRaises(ValidationError, validate_exchange_endpoint, "http://10.0.0.1/api")

	def test_blocks_bad_scheme(self):
		self.assertRaises(ValidationError, validate_exchange_endpoint, "ftp://example.com/api")

	@patch(
		"socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
	)
	def test_blocks_hostname_resolving_to_private(self, _mock):
		self.assertRaises(ValidationError, validate_exchange_endpoint, "http://localhost/api")

	@patch(
		"socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("52.84.10.1", 443))]
	)
	def test_allows_public_hostname(self, _mock):
		validate_exchange_endpoint("https://api.frankfurter.dev/v1/latest")

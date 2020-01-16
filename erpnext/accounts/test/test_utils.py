from __future__ import unicode_literals
import unittest
from erpnext.accounts.party import get_party_shipping_address
from frappe.test_runner import make_test_objects


class TestUtils(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		super(TestUtils, cls).setUpClass()
		make_test_objects('Address', ADDRESS_RECORDS)

	def test_get_party_shipping_address(self):
		address = get_party_shipping_address('Customer', '_Test Customer 1')
		self.assertEqual(address, '_Test Billing Address 2 Title-Billing')

	def test_get_party_shipping_address2(self):
		address = get_party_shipping_address('Customer', '_Test Customer 2')
		self.assertEqual(address, '_Test Shipping Address 2 Title-Shipping')


ADDRESS_RECORDS = [
	{
		"doctype": "Address",
		"address_type": "Billing",
		"address_line1": "Address line 1",
		"address_title": "_Test Billing Address Title",
		"city": "Lagos",
		"country": "Nigeria",
		"links": [
			{
				"link_doctype": "Customer",
				"link_name": "_Test Customer 2",
				"doctype": "Dynamic Link"
			}
		]
	},
	{
		"doctype": "Address",
		"address_type": "Shipping",
		"address_line1": "Address line 2",
		"address_title": "_Test Shipping Address 1 Title",
		"city": "Lagos",
		"country": "Nigeria",
		"links": [
			{
				"link_doctype": "Customer",
				"link_name": "_Test Customer 2",
				"doctype": "Dynamic Link"
			}
		]
	},
	{
		"doctype": "Address",
		"address_type": "Shipping",
		"address_line1": "Address line 3",
		"address_title": "_Test Shipping Address 2 Title",
		"city": "Lagos",
		"country": "Nigeria",
		"is_shipping_address": "1",
		"links": [
			{
				"link_doctype": "Customer",
				"link_name": "_Test Customer 2",
				"doctype": "Dynamic Link"
			}
		]
	},
	{
		"doctype": "Address",
		"address_type": "Billing",
		"address_line1": "Address line 4",
		"address_title": "_Test Billing Address 2 Title",
		"city": "Lagos",
		"country": "Nigeria",
		"is_shipping_address": "1",
		"links": [
			{
				"link_doctype": "Customer",
				"link_name": "_Test Customer 1",
				"doctype": "Dynamic Link"
			}
		]
	}
]

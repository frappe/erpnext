from __future__ import unicode_literals

import unittest

from frappe.test_runner import make_test_objects

from erpnext.accounts.party import get_party_shipping_address
from erpnext.accounts.utils import get_future_stock_vouchers, get_voucherwise_gl_entries
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt


class TestUtils(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		super(TestUtils, cls).setUpClass()
		make_test_objects("Address", ADDRESS_RECORDS)

	def test_get_party_shipping_address(self):
		address = get_party_shipping_address("Customer", "_Test Customer 1")
		self.assertEqual(address, "_Test Billing Address 2 Title-Billing")

	def test_get_party_shipping_address2(self):
		address = get_party_shipping_address("Customer", "_Test Customer 2")
		self.assertEqual(address, "_Test Shipping Address 2 Title-Shipping")

	def test_get_voucher_wise_gl_entry(self):

		pr = make_purchase_receipt(
			item_code="_Test Item",
			posting_date="2021-02-01",
			rate=100,
			qty=1,
			warehouse="Stores - TCP1",
			company="_Test Company with perpetual inventory",
		)

		future_vouchers = get_future_stock_vouchers("2021-01-01", "00:00:00", for_items=["_Test Item"])

		voucher_type_and_no = ("Purchase Receipt", pr.name)
		self.assertTrue(
			voucher_type_and_no in future_vouchers,
			msg="get_future_stock_vouchers not returning correct value",
		)

		posting_date = "2021-01-01"
		gl_entries = get_voucherwise_gl_entries(future_vouchers, posting_date)
		self.assertTrue(
			voucher_type_and_no in gl_entries, msg="get_voucherwise_gl_entries not returning expected GLes",
		)


ADDRESS_RECORDS = [
	{
		"doctype": "Address",
		"address_type": "Billing",
		"address_line1": "Address line 1",
		"address_title": "_Test Billing Address Title",
		"city": "Lagos",
		"country": "Nigeria",
		"links": [
			{"link_doctype": "Customer", "link_name": "_Test Customer 2", "doctype": "Dynamic Link"}
		],
	},
	{
		"doctype": "Address",
		"address_type": "Shipping",
		"address_line1": "Address line 2",
		"address_title": "_Test Shipping Address 1 Title",
		"city": "Lagos",
		"country": "Nigeria",
		"links": [
			{"link_doctype": "Customer", "link_name": "_Test Customer 2", "doctype": "Dynamic Link"}
		],
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
			{"link_doctype": "Customer", "link_name": "_Test Customer 2", "doctype": "Dynamic Link"}
		],
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
			{"link_doctype": "Customer", "link_name": "_Test Customer 1", "doctype": "Dynamic Link"}
		],
	},
]

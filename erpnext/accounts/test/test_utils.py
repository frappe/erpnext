import unittest

import frappe
from frappe.test_runner import make_test_objects

from erpnext.accounts.party import get_party_shipping_address
from erpnext.accounts.utils import (
	get_future_stock_vouchers,
	get_voucherwise_gl_entries,
	sort_stock_vouchers_by_posting_date,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


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
			voucher_type_and_no in gl_entries,
			msg="get_voucherwise_gl_entries not returning expected GLes",
		)

	def test_stock_voucher_sorting(self):
		vouchers = []

		item = make_item().name

		stock_entry = {"item": item, "to_warehouse": "_Test Warehouse - _TC", "qty": 1, "rate": 10}

		se1 = make_stock_entry(posting_date="2022-01-01", **stock_entry)
		se3 = make_stock_entry(posting_date="2022-03-01", **stock_entry)
		se2 = make_stock_entry(posting_date="2022-02-01", **stock_entry)

		for doc in (se1, se2, se3):
			vouchers.append((doc.doctype, doc.name))

		vouchers.append(("Stock Entry", "Wat"))

		sorted_vouchers = sort_stock_vouchers_by_posting_date(list(reversed(vouchers)))
		self.assertEqual(sorted_vouchers, vouchers)


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

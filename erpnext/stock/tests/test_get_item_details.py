import json

import frappe
from frappe.test_runner import make_test_objects, make_test_records_for_doctype
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.get_item_details import get_item_details

test_ignore = ["BOM"]
test_dependencies = ["Customer", "Supplier", "Item", "Price List", "Item Price"]


class TestGetItemDetail(FrappeTestCase):
	def setUp(self):
		make_test_objects("Price List")
		super().setUp()
		# delete_existing_item_and_price_list()
		# setup_customer_and_supplier()
		# setup_item_and_price_list()
		# frappe.call('erpnext.stock.get_item_detail.get_item_detail')

	def tearDown(self):
		pass
		# delete_existing_item_and_price_list()

	def test_get_item_detail_purchase_order(self):

		args = frappe._dict(
			{
				"item_code": "_Test Item",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"conversion_rate": 1.0,
				"selling_price_list": "_Test Selling Price List",
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1.0,
				"doctype": "Purchase Order",
				"name": None,
				"supplier": "_Test Supplier",
				"transaction_date": None,
				"conversion_rate": 1.0,
				"buying_price_list": "_Test Buying Price List",
				"is_subcontracted": 0,
				"ignore_pricing_rule": 0,
			}
		)
		details = get_item_details(args)
		self.assertEqual(details.get("price_list_rate"), 100)

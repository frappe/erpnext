import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.utils import make_test_records

from erpnext.stock.get_item_details import get_item_details

test_dependencies = ["Customer", "Supplier", "Item", "Price List", "Item Price"]


class TestGetItemDetail(IntegrationTestCase):
	def setUp(self):
		make_test_records("Price List")
		super().setUp()

	def test_get_item_detail_purchase_order(self):
		args = frappe._dict(
			{
				"item_code": "_Test Item",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"conversion_rate": 1.0,
				"price_list_currency": "USD",
				"plc_conversion_rate": 1.0,
				"doctype": "Purchase Order",
				"name": None,
				"supplier": "_Test Supplier",
				"transaction_date": None,
				"price_list": "_Test Buying Price List",
				"is_subcontracted": 0,
				"ignore_pricing_rule": 1,
				"qty": 1,
			}
		)
		details = get_item_details(args)
		self.assertEqual(details.get("price_list_rate"), 100)

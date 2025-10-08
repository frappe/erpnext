import frappe
from frappe.tests.utils import FrappeTestCase

import erpnext.stock.report.item_prices.item_prices as item_prices
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse


class TestItemPrices(FrappeTestCase):
	def setUp(self):
		self.test_items = []
		for i in range(1, 3):
			item_data = {
				"doctype": "Item",
				"item_code": f"Test Item 1 {i}",
				"item_name": f"Test Item Name 1 {i}",
				"description": f"Test Description 1 {i}",
				"stock_uom": "Nos",
				"item_group": "Products",
				"disabled": 0 if i == 1 else 1,
			}
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"
			item = frappe.get_doc(item_data)
			item.insert(ignore_permissions=True, ignore_if_duplicate=True)
			self.test_items.append(item.name)

	def test_execute_no_filters_T_IP_001(self):
		item_prices.get_item_details = lambda filters: {
			self.test_items[0]: {
				"item_name": "Test Item Name 1",
				"item_group": "Products",
				"description": "Test Description 1",
				"stock_uom": "Nos",
				"brand": "",
			}
		}
		item_prices.get_price_list = lambda: {}
		item_prices.get_last_purchase_rate = lambda: {self.test_items[0]: 150.0}
		item_prices.get_item_bom_rate = lambda: {self.test_items[0]: 120.0}
		item_prices.get_valuation_rate = lambda: {self.test_items[0]: 100.0}

		columns, data = item_prices.execute()

		self.assertTrue(columns, "Report should return columns.")
		self.assertEqual(data[0][0], self.test_items[0], "First item's code should match the test item.")

	def test_get_item_details_enabled_T_IP_002(self):
		filters = {"items": "Enabled Items only"}
		result = item_prices.get_item_details(filters)
		self.assertIn(self.test_items[0], result)
		self.assertNotIn(self.test_items[1], result)

	def test_get_item_details_disabled_T_IP_003(self):
		filters = {"items": "Disabled Items only"}
		result = item_prices.get_item_details(filters)
		self.assertIn(self.test_items[1], result)
		self.assertNotIn(self.test_items[0], result)

	def test_get_price_list_T_IP_004(self):
		if not frappe.db.exists("Currency", "INR"):
			frappe.get_doc({"doctype": "Currency", "name": "INR", "symbol": "₹"}).insert(
				ignore_permissions=True, ignore_if_duplicate=True
			)

		frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": "Test PL",
				"enabled": 1,
				"buying": 1,
				"currency": "INR",
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": self.test_items[0],
				"price_list": "Test PL",
				"price_list_rate": 500,
				"buying": 1,
				"selling": 0,
				"currency": "INR",
			}
		).insert(ignore_permissions=True)

		result = item_prices.get_price_list()
		self.assertIn(self.test_items[0], result)
		self.assertIn("Buying", result[self.test_items[0]])
		self.assertIn("₹ 500.0", result[self.test_items[0]]["Buying"])

	def test_get_valuation_rate_T_IP_005(self):
		frappe.get_doc(
			{
				"doctype": "Bin",
				"item_code": self.test_items[0],
				"warehouse": create_warehouse("Test Warehouse", company="_Test Company"),
				"actual_qty": 10,
				"valuation_rate": 50,
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		result = item_prices.get_valuation_rate()
		self.assertIn(self.test_items[0], result)
		self.assertEqual(result[self.test_items[0]], 50)

	def test_get_last_purchase_rate_T_IP_006(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": "_Test Company",
				"supplier": "Test Supplier",
				"transaction_date": frappe.utils.nowdate(),
				"schedule_date": frappe.utils.nowdate(),
				"docstatus": 1,
				"items": [
					{
						"item_code": self.test_items[0],
						"warehouse": create_warehouse("Test Warehouse", company="_Test Company"),
						"qty": 1,
						"rate": 300,
					}
				],
			}
		).insert(ignore_permissions=True)

		result = item_prices.get_last_purchase_rate()
		self.assertIn(self.test_items[0], result)
		self.assertEqual(result[self.test_items[0]], 300)

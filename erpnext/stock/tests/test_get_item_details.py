import frappe
from frappe.tests import IntegrationTestCase

from erpnext.stock.get_item_details import get_item_details

EXTRA_TEST_RECORD_DEPENDENCIES = ["Customer", "Supplier", "Item", "Price List", "Item Price"]


class TestGetItemDetail(IntegrationTestCase):
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

	# making this test in get_item_details test file as feat/fix is present in that method
	def test_fetch_price_from_list_rate_on_doc_save(self):
		# create item
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "Test Item with Batch",
				"item_name": "Test Item with Batch",
				"item_group": "All Item Groups",
				"is_stock_item": 1,
				"has_batch_no": 1,
			}
		).insert()

		# create batch
		frappe.get_doc(
			{
				"doctype": "Batch",
				"batch_id": "BATCH01",
				"item": item.name,
			}
		).insert()

		# create item price
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": "Standard Selling",
				"item_code": item.item_code,
				"price_list_rate": 50,
				"batch_no": "BATCH01",
			}
		).insert()

		# create purchase receipt to have some stock for delivery
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		make_purchase_receipt(
			item_code=item.item_code,
			warehouse="_Test Warehouse - _TC",
			qty=100,
			rate=100,
			batch_no="BATCH01",
		)

		# creating sales order just to create delivery note from it
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order(item_code=item.item_code, qty=2, rate=75)

		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

		dn = make_delivery_note(so.name)

		# Test 1 : On creation of DN, item's batch won't be fetched and rate will remaing the same as in SO
		self.assertIsNone(dn.items[0].batch_no)
		self.assertEqual(dn.items[0].rate, 75)

		# Test 2 : On saving the DN, item's batch will be fetched and rate will be updated from Item Price
		dn.save()
		self.assertEqual(dn.items[0].batch_no, "BATCH01")
		self.assertEqual(dn.items[0].rate, 50)

# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe

import unittest, os, json
from frappe.utils import cstr
from erpnext.erpnext_integrations.connectors.shopify_connection import create_order
from erpnext.erpnext_integrations.doctype.shopify_settings.sync_product import make_item
from erpnext.erpnext_integrations.doctype.shopify_settings.sync_customer import create_customer
from frappe.core.doctype.data_import.data_import import import_doc
from erpnext.stock.doctype.item.test_item import make_item


class ShopifySettings(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")

		# use the fixture data
		import_doc(path=frappe.get_app_path("erpnext", "erpnext_integrations/doctype/shopify_settings/test_data/custom_field.json"),
			ignore_links=True, overwrite=True)

		frappe.reload_doctype("Customer")
		frappe.reload_doctype("Sales Order")
		frappe.reload_doctype("Delivery Note")
		frappe.reload_doctype("Sales Invoice")

		self.setup_shopify()

	def setup_shopify(self):
		shopify_settings = frappe.get_doc("Shopify Settings")
		shopify_settings.taxes = []

		shopify_settings.update({
			"app_type": "Private",
			"shopify_url": "test.myshopify.com",
			"api_key": "17702c7c4452b9c5d235240b6e7a39da",
			"password": "17702c7c4452b9c5d235240b6e7a39da",
			"shared_secret": "17702c7c4452b9c5d235240b6e7a39da",
			"price_list": "_Test Price List",
			"warehouse": "_Test Warehouse - _TC",
			"cash_bank_account": "Cash - _TC",
			"account": "Cash - _TC",
			"customer_group": "_Test Customer Group",
			"cost_center": "Main - _TC",
			"taxes": [
				{
					"shopify_tax": "International Shipping",
					"tax_account":"Legal Expenses - _TC"
				}
			],
			"enable_shopify": 0,
			"sales_order_series": "SO-",
			"sync_sales_invoice": 1,
			"sales_invoice_series": "SINV-",
			"sync_delivery_note": 1,
			"delivery_note_series": "DN-"
		}).save(ignore_permissions=True)

		self.shopify_settings = shopify_settings

	def test_order(self):
		### Create Customer ###
		with open (os.path.join(os.path.dirname(__file__), "test_data", "shopify_customer.json")) as shopify_customer:
			shopify_customer = json.load(shopify_customer)
		create_customer(shopify_customer.get("customer"), self.shopify_settings)

		### Create Item ###
		with open (os.path.join(os.path.dirname(__file__), "test_data", "shopify_item.json")) as shopify_item:
			shopify_item = json.load(shopify_item)
		make_item("_Test Warehouse - _TC", shopify_item.get("product"))


		### Create Order ###
		with open (os.path.join(os.path.dirname(__file__), "test_data", "shopify_order.json")) as shopify_order:
			shopify_order = json.load(shopify_order)

		create_order(shopify_order.get("order"), self.shopify_settings, False, company="_Test Company")

		sales_order = frappe.get_doc("Sales Order", {"shopify_order_id": cstr(shopify_order.get("order").get("id"))})

		self.assertEqual(cstr(shopify_order.get("order").get("id")), sales_order.shopify_order_id)

		#check for customer
		shopify_order_customer_id = cstr(shopify_order.get("order").get("customer").get("id"))
		sales_order_customer_id = frappe.get_value("Customer", sales_order.customer, "shopify_customer_id")

		self.assertEqual(shopify_order_customer_id, sales_order_customer_id)

		#check sales invoice
		sales_invoice = frappe.get_doc("Sales Invoice", {"shopify_order_id": sales_order.shopify_order_id})
		self.assertEqual(sales_invoice.rounded_total, sales_order.rounded_total)

		#check delivery note
		delivery_note_count = frappe.db.sql("""select count(*) from `tabDelivery Note`
			where shopify_order_id = %s""", sales_order.shopify_order_id)[0][0]

		self.assertEqual(delivery_note_count, len(shopify_order.get("order").get("fulfillments")))

	def test_product_sync_using_integration_item():
		# Create erpnext item
		item = make_item("_Test Shopify Item")

		# Add Integration Item
		frappe.get_doc({
			"doctype":"Integration Item",
			"integration_item": "Protein Bar"
			"erpnext_item_code": "_Test Shopify Item"
		}).insert()

		shopify_order_json = {
			"id": 3669049704638,
			"email": "frappe@maplestores.com",
			"created_at": "2021-03-12T13:38:34+05:30",
			"updated_at": "2021-03-12T13:38:35+05:30",
			"number": 8,
			"note": "",
			"token": "88d2c4051b4b13e268ebb6ed409db82a",
			"gateway": "manual",
			"test": false,
			"total_price": "165200.00",
			"subtotal_price": "140000.00",
			"total_weight": 0,
			"total_tax": "25200.00",
			"taxes_included": false,
			"currency": "INR",
			"financial_status": "pending",
			"confirmed": true,
			"total_discounts": "0.00",
			"total_line_items_price": "140000.00",
			"buyer_accepts_marketing": false,
			"name": "#1008",
			"total_price_usd": "2272.11",
			"user_id": 71496466622,
			"location_id": 61178446014,
			"processed_at": "2021-03-12T13:38:34+05:30",
			"customer_locale": "en",
			"app_id": 1354745,
			"order_number": 1008,
			"discount_applications": [],
			"discount_codes": [],
			"note_attributes": [],
			"payment_gateway_names": [
				"manual"
			],
			"processing_method": "manual",
			"source_name": "shopify_draft_order",
			"tax_lines": [
				{
					"price": "25200.00",
					"rate": 0.18,
					"title": "IGST",
					"price_set": {
						"shop_money": {
							"amount": "25200.00",
							"currency_code": "INR"
						},
						"presentment_money": {
							"amount": "25200.00",
							"currency_code": "INR"
						}
					}
				}
			],
			"tags": "",
			"contact_email": "frappe@maplestores.com",
			"presentment_currency": "INR",
			"total_line_items_price_set": {
				"shop_money": {
					"amount": "140000.00",
					"currency_code": "INR"
				},
				"presentment_money": {
					"amount": "140000.00",
					"currency_code": "INR"
				}
			},
			"total_discounts_set": {
				"shop_money": {
					"amount": "0.00",
					"currency_code": "INR"
				},
				"presentment_money": {
					"amount": "0.00",
					"currency_code": "INR"
				}
			},
			"total_shipping_price_set": {
				"shop_money": {
					"amount": "0.00",
					"currency_code": "INR"
				},
				"presentment_money": {
					"amount": "0.00",
					"currency_code": "INR"
				}
			},
			"subtotal_price_set": {
				"shop_money": {
					"amount": "140000.00",
					"currency_code": "INR"
				},
				"presentment_money": {
					"amount": "140000.00",
					"currency_code": "INR"
				}
			},
			"total_price_set": {
				"shop_money": {
					"amount": "165200.00",
					"currency_code": "INR"
				},
				"presentment_money": {
					"amount": "165200.00",
					"currency_code": "INR"
				}
			},
			"total_tax_set": {
				"shop_money": {
					"amount": "25200.00",
					"currency_code": "INR"
				},
				"presentment_money": {
					"amount": "25200.00",
					"currency_code": "INR"
				}
			},
			"line_items": [
				{
					"id": 9645225836734,
					"variant_id": 39351752425662,
					"title": "Protein Bar",
					"quantity": 1,
					"sku": "",
					"variant_title": null,
					"vendor": "Maple Stores Mumbai",
					"fulfillment_service": "manual",
					"product_id": 6565573427390,
					"requires_shipping": true,
					"taxable": true,
					"gift_card": false,
					"name": "Protein Bar",
					"variant_inventory_management": "shopify",
					"properties": [],
					"product_exists": true,
					"fulfillable_quantity": 1,
					"grams": 0,
					"price": "140000.00",
					"total_discount": "0.00",
					"fulfillment_status": null,
					"price_set": {
						"shop_money": {
							"amount": "140000.00",
							"currency_code": "INR"
						},
						"presentment_money": {
							"amount": "140000.00",
							"currency_code": "INR"
						}
					},
					"total_discount_set": {
						"shop_money": {
							"amount": "0.00",
							"currency_code": "INR"
						},
						"presentment_money": {
							"amount": "0.00",
							"currency_code": "INR"
						}
					},
					"discount_allocations": [],
					"duties": [],
					"tax_lines": [
						{
							"title": "IGST",
							"price": "25200.00",
							"rate": 0.18,
							"price_set": {
								"shop_money": {
									"amount": "25200.00",
									"currency_code": "INR"
								},
								"presentment_money": {
									"amount": "25200.00",
									"currency_code": "INR"
								}
							}
						}
					]
				}
			],
			"fulfillments": [],
			"refunds": [],
			"total_tip_received": "0.0",
			"shipping_lines": [],
			"customer": {
				"id": 5049858588862,
				"email": "frappe@maplestores.com",
				"accepts_marketing": false,
				"created_at": "2021-03-10T19:57:40+05:30",
				"updated_at": "2021-03-12T13:38:35+05:30",
				"first_name": "Frappe Technologies",
				"last_name": "",
				"orders_count": 5,
				"state": "disabled",
				"total_spent": "731600.00",
				"last_order_id": 3669049704638,
				"note": "",
				"verified_email": true,
				"tags": "",
				"last_order_name": "#1008",
				"currency": "INR",
				"accepts_marketing_updated_at": "2021-03-10T19:57:40+05:30",
			}
		}
		# Create Order
		create_order(shopify_order_json, self.shopify_settings, False, company="_Test Company")


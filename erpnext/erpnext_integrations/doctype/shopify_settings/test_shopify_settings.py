# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import os
import json
import frappe
import unittest
from frappe.utils import cint, cstr, flt
from frappe.utils.fixtures import sync_fixtures
from erpnext_shopify.sync_orders import create_order, valid_customer_and_product
from erpnext_shopify.sync_products import make_item
from erpnext_shopify.sync_customers import create_customer

class ShopifySettings(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		sync_fixtures("erpnext_shopify")
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
			"price_list": "_Test Price List",
			"warehouse": "_Test Warehouse - _TC",
			"cash_bank_account": "Cash - _TC",
			"customer_group": "_Test Customer Group",
			"taxes": [
				{
					"shopify_tax": "International Shipping",
					"tax_account":"Legal Expenses - _TC"
				}
			],
			"enable_shopify": 0,
			"sales_order_series": "SO-",
			"sales_invoice_series": "SINV-",
			"delivery_note_series": "DN-"
		}).save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		
		records = {
			"Sales Invoice": [{"shopify_order_id": "2414345735"}],
			"Delivery Note": [{"shopify_order_id": "2414345735"}],
			"Sales Order": [{"shopify_order_id": "2414345735"}],
			"Item": [{"shopify_product_id" :"4059739520"},{"shopify_product_id": "13917612359"}, 
				{"shopify_product_id": "13917612423"}, {"shopify_product_id":"13917612487"}],
			"Address": [{"shopify_address_id": "2476804295"}],
			"Customer": [{"shopify_customer_id": "2324518599"}]
		}
		
		for doctype in ["Sales Invoice", "Delivery Note", "Sales Order", "Item", "Address", "Customer"]:
			for filters in records[doctype]:
				for record in frappe.get_all(doctype, filters=filters):
					if doctype not in ["Customer", "Item", "Address"]:
						doc = frappe.get_doc(doctype, record.name)
						if doc.docstatus == 1:
							doc.cancel()
					frappe.delete_doc(doctype, record.name)

	def test_product(self):
		with open (os.path.join(os.path.dirname(__file__), "test_data", "shopify_item.json")) as shopify_item:
			shopify_item = json.load(shopify_item)

		make_item("_Test Warehouse - _TC", shopify_item.get("product"), [])

		item = frappe.get_doc("Item", cstr(shopify_item.get("product").get("id")))

		self.assertEqual(cstr(shopify_item.get("product").get("id")), item.shopify_product_id)
		self.assertEqual(item.sync_with_shopify, 1)

		#test variant price
		for variant in shopify_item.get("product").get("variants"):
			price = frappe.get_value("Item Price",
				{"price_list": "_Test Price List", "item_code": cstr(variant.get("id"))}, "price_list_rate")
			self.assertEqual(flt(variant.get("price")), flt(price))

	def test_customer(self):
		with open (os.path.join(os.path.dirname(__file__), "test_data", "shopify_customer.json")) as shopify_customer:
			shopify_customer = json.load(shopify_customer)

		create_customer(shopify_customer.get("customer"), [])

		customer = frappe.get_doc("Customer", {"shopify_customer_id": cstr(shopify_customer.get("customer").get("id"))})

		self.assertEqual(customer.sync_with_shopify, 1)

		shopify_address = shopify_customer.get("customer").get("addresses")[0]
		address = frappe.get_doc("Address", {"customer": customer.name})

		self.assertEqual(cstr(shopify_address.get("id")), address.shopify_address_id)
	
	def test_order(self):
		with open (os.path.join(os.path.dirname(__file__), "test_data", "shopify_customer.json")) as shopify_customer:
			shopify_customer = json.load(shopify_customer)
			
		create_customer(shopify_customer.get("customer"), [])
		
		with open (os.path.join(os.path.dirname(__file__), "test_data", "shopify_item.json")) as shopify_item:
			shopify_item = json.load(shopify_item)

		make_item("_Test Warehouse - _TC", shopify_item.get("product"), [])
				
		with open (os.path.join(os.path.dirname(__file__), "test_data", "shopify_order.json")) as shopify_order:
			shopify_order = json.load(shopify_order)

		shopify_settings = frappe.get_doc("Shopify Settings", "Shopify Settings")
		
		create_order(shopify_order.get("order"), shopify_settings, "_Test Company")

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
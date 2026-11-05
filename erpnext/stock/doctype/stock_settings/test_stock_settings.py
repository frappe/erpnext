# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase, change_settings


class TestStockSettings(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("Stock Settings", "clean_description_html", 0)

	def test_settings(self):
		item = frappe.get_doc(
			dict(
				doctype="Item",
				item_code="Item for description test",
				item_group="Products",
				description='<p><span style="font-size: 12px;">Drawing No. 07-xxx-PO132<br></span><span style="font-size: 12px;">1800 x 1685 x 750<br></span><span style="font-size: 12px;">All parts made of Marine Ply<br></span><span style="font-size: 12px;">Top w/ Corian dd<br></span><span style="font-size: 12px;">CO, CS, VIP Day Cabin</span></p>',
			)
		).insert()

		settings = frappe.get_single("Stock Settings")
		settings.clean_description_html = 1
		settings.save()

		item.reload()

		self.assertEqual(
			item.description,
			"<p>Drawing No. 07-xxx-PO132<br>1800 x 1685 x 750<br>All parts made of Marine Ply<br>Top w/ Corian dd<br>CO, CS, VIP Day Cabin</p>",
		)

		item.delete()

	def test_clean_html(self):
		settings = frappe.get_single("Stock Settings")
		settings.clean_description_html = 1
		settings.save()

		item = frappe.get_doc(
			dict(
				doctype="Item",
				item_code="Item for description test",
				item_group="Products",
				description='<p><span style="font-size: 12px;">Drawing No. 07-xxx-PO132<br></span><span style="font-size: 12px;">1800 x 1685 x 750<br></span><span style="font-size: 12px;">All parts made of Marine Ply<br></span><span style="font-size: 12px;">Top w/ Corian dd<br></span><span style="font-size: 12px;">CO, CS, VIP Day Cabin</span></p>',
			)
		).insert()

		self.assertEqual(
			item.description,
			"<p>Drawing No. 07-xxx-PO132<br>1800 x 1685 x 750<br>All parts made of Marine Ply<br>Top w/ Corian dd<br>CO, CS, VIP Day Cabin</p>",
		)

		item.delete()

	@change_settings(
		"Stock Settings",
		{
			"auto_insert_price_list_rate_if_missing": 1,
			"update_existing_price_list_rate": 1,
			"update_price_list_based_on": "Rate",
		},
	)
	def test_auto_price_update_keeps_other_customer_price(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.get_item_details import insert_item_price

		item = make_item(properties={"is_stock_item": 1})
		customer_price = frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": "Standard Selling",
				"item_code": item.name,
				"customer": "_Test Customer",
				"price_list_rate": 900,
			}
		).insert()

		insert_item_price(
			frappe._dict(
				price_list="Standard Selling",
				item_code=item.name,
				currency=customer_price.currency,
				stock_uom=item.stock_uom,
				conversion_factor=1,
				rate=1500,
				customer="_Test Customer 1",
			)
		)

		self.assertEqual(frappe.db.get_value("Item Price", customer_price.name, "price_list_rate"), 900)
		self.assertTrue(
			frappe.db.exists(
				"Item Price",
				{
					"item_code": item.name,
					"price_list": "Standard Selling",
					"customer": ("is", "not set"),
					"price_list_rate": 1500,
				},
			)
		)

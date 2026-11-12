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

	@change_settings(
		"Stock Settings",
		{"over_delivery_receipt_allowance": 0, "role_allowed_to_over_deliver_receive": None},
	)
	def test_over_delivery_role_kept_with_zero_allowance(self):
		settings = frappe.get_doc("Stock Settings")
		settings.over_delivery_receipt_allowance = 0
		settings.role_allowed_to_over_deliver_receive = "Stock Manager"
		settings.save()

		self.assertEqual(
			frappe.db.get_single_value("Stock Settings", "role_allowed_to_over_deliver_receive"),
			"Stock Manager",
		)

	def test_boot_cache_cleared_when_boot_setting_changes(self):
		frappe.cache.hset("bootinfo", frappe.session.user, {"cached": 1})
		settings = frappe.get_doc("Stock Settings")
		settings.disable_serial_no_and_batch_selector = (
			0 if settings.disable_serial_no_and_batch_selector else 1
		)
		settings.save()

		self.assertIsNone(frappe.cache.hget("bootinfo", frappe.session.user))

	@change_settings("Stock Settings", {"show_barcode_field": 1})
	def test_hiding_barcode_field_keeps_item_barcodes(self):
		settings = frappe.get_doc("Stock Settings")
		settings.show_barcode_field = 0
		settings.save()

		def is_hidden(doctype, fieldname):
			return frappe.db.get_value(
				"Property Setter",
				{"doc_type": doctype, "field_name": fieldname, "property": "hidden"},
				"value",
			)

		self.assertEqual(is_hidden("Delivery Note", "scan_barcode"), "1")
		self.assertNotEqual(is_hidden("Item", "barcodes"), "1")
		self.assertNotEqual(is_hidden("Job Card", "barcode"), "1")

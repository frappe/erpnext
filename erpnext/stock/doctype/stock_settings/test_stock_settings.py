# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from unittest.mock import patch

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestStockSettings(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("Stock Settings", "clean_description_html", 0)

	def test_settings(self):
		item = frappe.get_doc(
			doctype="Item",
			item_code="Item for description test",
			item_group="Products",
			description='<p><span style="font-size: 12px;">Drawing No. 07-xxx-PO132<br></span><span style="font-size: 12px;">1800 x 1685 x 750<br></span><span style="font-size: 12px;">All parts made of Marine Ply<br></span><span style="font-size: 12px;">Top w/ Corian dd<br></span><span style="font-size: 12px;">CO, CS, VIP Day Cabin</span></p>',
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
			doctype="Item",
			item_code="Item for description test",
			item_group="Products",
			description='<p><span style="font-size: 12px;">Drawing No. 07-xxx-PO132<br></span><span style="font-size: 12px;">1800 x 1685 x 750<br></span><span style="font-size: 12px;">All parts made of Marine Ply<br></span><span style="font-size: 12px;">Top w/ Corian dd<br></span><span style="font-size: 12px;">CO, CS, VIP Day Cabin</span></p>',
		).insert()

		self.assertEqual(
			item.description,
			"<p>Drawing No. 07-xxx-PO132<br>1800 x 1685 x 750<br>All parts made of Marine Ply<br>Top w/ Corian dd<br>CO, CS, VIP Day Cabin</p>",
		)

		item.delete()

	def test_unrelated_change_does_not_update_item_metadata(self):
		settings = frappe.get_single("Stock Settings")
		settings.allow_partial_reservation = not settings.allow_partial_reservation

		with (
			patch("erpnext.utilities.naming.set_by_naming_series") as set_by_naming_series,
			patch("frappe.make_property_setter") as make_property_setter,
		):
			settings.save()

		set_by_naming_series.assert_not_called()
		make_property_setter.assert_not_called()

	def test_item_metadata_updates_when_related_settings_change(self):
		settings = frappe.get_single("Stock Settings")
		settings.item_naming_by = (
			"Item Code" if settings.item_naming_by == "Naming Series" else "Naming Series"
		)
		settings.show_barcode_field = not settings.show_barcode_field

		with (
			patch("erpnext.utilities.naming.set_by_naming_series") as set_by_naming_series,
			patch("frappe.make_property_setter") as make_property_setter,
		):
			settings.save()

		from erpnext.stock.doctype.stock_settings.stock_settings import get_transaction_barcode_fields

		set_by_naming_series.assert_called_once()
		self.assertEqual(make_property_setter.call_count, len(get_transaction_barcode_fields()))

	def test_cannot_disable_serial_and_batch_with_tracked_items(self):
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Serial Deactivation Item", {"has_serial_no": 1})

		settings = frappe.get_single("Stock Settings")
		settings.enable_serial_and_batch_no_for_item = 0

		exists = frappe.db.exists

		def exists_without_bundles(doctype, *args, **kwargs):
			# test data has submitted bundles, which would throw before the item check
			return doctype != "Serial and Batch Bundle" and exists(doctype, *args, **kwargs)

		with (
			patch.object(frappe.db, "exists", side_effect=exists_without_bundles),
			self.assertRaisesRegex(frappe.ValidationError, "items with serial / batch enabled"),
		):
			settings.save()

	def test_company_valuation_method_drives_reposting(self):
		from frappe.utils import add_days, today

		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		frappe.db.set_single_value("Stock Settings", "valuation_method", "Standard Cost")
		frappe.db.set_value("Company", "_Test Company", "valuation_method", "FIFO")
		item = make_item(properties={"is_stock_item": 1, "valuation_method": ""}).name
		warehouse = "_Test Warehouse - _TC"

		make_stock_entry(item_code=item, target=warehouse, qty=10, rate=100)
		issue = make_stock_entry(item_code=item, source=warehouse, qty=5)
		make_stock_entry(
			item_code=item, target=warehouse, qty=10, rate=200, posting_date=add_days(today(), -1)
		)

		issue_value = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": issue.name, "is_cancelled": 0}, "stock_value_difference"
		)
		self.assertEqual(issue_value, -1000)
		self.assertEqual(
			frappe.db.get_value("Bin", {"item_code": item, "warehouse": warehouse}, "stock_value"), 2000
		)

	def test_split_batch_uses_warehouse_company_valuation(self):
		from erpnext.stock.doctype.batch.batch import split_batch
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
			get_batch_from_bundle,
		)
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		frappe.db.set_single_value(
			"Stock Settings", {"do_not_use_batchwise_valuation": 1, "valuation_method": "Moving Average"}
		)
		frappe.db.set_value("Company", "_Test Company 1", "valuation_method", "FIFO")
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SPLITCO-.####",
				"valuation_method": "",
			}
		).name
		warehouse = "Stores - _TC1"
		receipt = make_stock_entry(
			item_code=item, target=warehouse, qty=10, rate=100, company="_Test Company 1"
		)

		new_batch = split_batch(
			get_batch_from_bundle(receipt.items[0].serial_and_batch_bundle), item, warehouse, 4
		)

		self.assertEqual(frappe.db.get_value("Batch", new_batch, "use_batchwise_valuation"), 1)

	@ERPNextTestSuite.change_settings(
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

	def test_over_delivery_role_kept_with_zero_allowance(self):
		settings = frappe.get_doc("Stock Settings")
		settings.over_delivery_receipt_allowance = 0
		settings.role_allowed_to_over_deliver_receive = "Stock Manager"
		settings.save()

		self.assertEqual(
			frappe.db.get_single_value("Stock Settings", "role_allowed_to_over_deliver_receive"),
			"Stock Manager",
		)

	def test_hiding_barcode_field_keeps_item_barcodes(self):
		settings = frappe.get_doc("Stock Settings")
		settings.show_barcode_field = 1
		settings.save()
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

	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_uom_with_conversion_rate_defined_in_item": 1})
	def test_stock_entry_uom_must_be_defined_in_item(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(properties={"is_stock_item": 1, "stock_uom": "Kg"}).name
		stock_entry = make_stock_entry(
			item_code=item, target="_Test Warehouse - _TC", qty=2, rate=100, do_not_save=True
		)
		stock_entry.items[0].update({"uom": "Tonne", "conversion_factor": 1000})

		self.assertRaises(frappe.ValidationError, stock_entry.insert)

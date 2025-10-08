# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
import random
import re

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.test_runner import make_test_objects
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, today

from erpnext.controllers.item_variant import (
	InvalidItemAttributeValueError,
	ItemVariantExistsError,
	create_variant,
	get_variant,
)
from erpnext.stock.doctype.item.item import (
	DataValidationError,
	InvalidBarcode,
	StockExistsForTemplate,
	get_item_attribute,
	get_timeline_data,
	get_uom_conv_factor,
	validate_is_stock_item,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.warehouse import convert_to_group_or_ledger
from erpnext.stock.get_item_details import get_item_details

test_ignore = ["BOM"]
test_dependencies = ["Warehouse", "Item Group", "Item Tax Template", "Brand", "Item Attribute"]


def make_item(item_code=None, properties=None, uoms=None, barcode=None):
	if not item_code:
		item_code = frappe.generate_hash(length=16)

	if frappe.db.exists("Item", item_code):
		return frappe.get_doc("Item", item_code)

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_code,
			"description": item_code,
			"item_group": "Products",
		}
	)

	if properties:
		item.update(properties)

	if item.is_stock_item:
		for item_default in [doc for doc in item.get("item_defaults") if not doc.default_warehouse]:
			item_default.default_warehouse = "_Test Warehouse - _TC"
			item_default.company = "_Test Company"

	if uoms:
		for uom in uoms:
			item.append("uoms", uom)

	if barcode:
		item.append(
			"barcodes",
			{
				"barcode": barcode,
			},
		)
	if "india_compliance" in frappe.get_installed_apps():
		from india_compliance.gst_india.utils import get_hsn_settings

		valid_hsn_length = get_hsn_settings()

		gst_hsn_code = frappe.db.get_all("GST HSN Code", pluck="name")
		for code in gst_hsn_code:
			if len(code) in valid_hsn_length[1]:
				item.gst_hsn_code = code
				break
	item.insert(ignore_permissions=True)

	return item


class TestItem(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.flags.attribute_values = None

	def get_item(self, idx):
		item_code = test_records[idx].get("item_code")
		if not frappe.db.exists("Item", item_code):
			item = frappe.copy_doc(test_records[idx])
			item.insert()
		else:
			item = frappe.get_doc("Item", item_code)
		return item

	def test_get_item_details(self):
		# delete modified item price record and make as per test_records
		frappe.db.sql("""delete from `tabItem Price`""")
		frappe.db.sql("""delete from `tabBin`""")

		to_check = {
			"item_code": "_Test Item",
			"item_name": "_Test Item",
			"description": "_Test Item 1",
			"warehouse": "_Test Warehouse - _TC",
			"income_account": "Sales - _TC",
			"expense_account": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"qty": 1.0,
			"price_list_rate": 100.0,
			"base_price_list_rate": 0.0,
			"discount_percentage": 0.0,
			"rate": 0.0,
			"base_rate": 0.0,
			"amount": 0.0,
			"base_amount": 0.0,
			"batch_no": None,
			"uom": "_Test UOM",
			"conversion_factor": 1.0,
			"reserved_qty": 1,
			"actual_qty": 5,
			"projected_qty": 14,
		}

		make_test_objects("Item Price")
		make_test_objects(
			"Bin",
			[
				{
					"item_code": "_Test Item",
					"warehouse": "_Test Warehouse - _TC",
					"reserved_qty": 1,
					"actual_qty": 5,
					"ordered_qty": 10,
					"projected_qty": 14,
				}
			],
		)

		company = "_Test Company"
		currency = frappe.get_cached_value("Company", company, "default_currency")

		details = get_item_details(
			{
				"item_code": "_Test Item",
				"company": company,
				"price_list": "_Test Price List",
				"currency": currency,
				"doctype": "Sales Order",
				"conversion_rate": 1,
				"price_list_currency": currency,
				"plc_conversion_rate": 1,
				"order_type": "Sales",
				"customer": "_Test Customer",
				"conversion_factor": 1,
				"price_list_uom_dependant": 1,
				"ignore_pricing_rule": 1,
			}
		)

		for key, value in to_check.items():
			self.assertEqual(value, details.get(key), key)

	def test_item_tax_template(self):
		expected_item_tax_template = [
			{
				"item_code": "_Test Item With Item Tax Template",
				"tax_category": "",
				"item_tax_template": "_Test Account Excise Duty @ 10 - _TC",
			},
			{
				"item_code": "_Test Item With Item Tax Template",
				"tax_category": "_Test Tax Category 1",
				"item_tax_template": "_Test Account Excise Duty @ 12 - _TC",
			},
			{
				"item_code": "_Test Item With Item Tax Template",
				"tax_category": "_Test Tax Category 2",
				"item_tax_template": None,
			},
			{
				"item_code": "_Test Item Inherit Group Item Tax Template 1",
				"tax_category": "",
				"item_tax_template": "_Test Account Excise Duty @ 10 - _TC",
			},
			{
				"item_code": "_Test Item Inherit Group Item Tax Template 1",
				"tax_category": "_Test Tax Category 1",
				"item_tax_template": "_Test Account Excise Duty @ 12 - _TC",
			},
			{
				"item_code": "_Test Item Inherit Group Item Tax Template 1",
				"tax_category": "_Test Tax Category 2",
				"item_tax_template": None,
			},
			{
				"item_code": "_Test Item Inherit Group Item Tax Template 2",
				"tax_category": "",
				"item_tax_template": "_Test Account Excise Duty @ 15 - _TC",
			},
			{
				"item_code": "_Test Item Inherit Group Item Tax Template 2",
				"tax_category": "_Test Tax Category 1",
				"item_tax_template": "_Test Account Excise Duty @ 12 - _TC",
			},
			{
				"item_code": "_Test Item Inherit Group Item Tax Template 2",
				"tax_category": "_Test Tax Category 2",
				"item_tax_template": None,
			},
			{
				"item_code": "_Test Item Override Group Item Tax Template",
				"tax_category": "",
				"item_tax_template": "_Test Account Excise Duty @ 20 - _TC",
			},
			{
				"item_code": "_Test Item Override Group Item Tax Template",
				"tax_category": "_Test Tax Category 1",
				"item_tax_template": "_Test Item Tax Template 1 - _TC",
			},
			{
				"item_code": "_Test Item Override Group Item Tax Template",
				"tax_category": "_Test Tax Category 2",
				"item_tax_template": None,
			},
		]

		expected_item_tax_map = {
			None: {},
			"_Test Account Excise Duty @ 10 - _TC": {"_Test Account Excise Duty - _TC": 10},
			"_Test Account Excise Duty @ 12 - _TC": {"_Test Account Excise Duty - _TC": 12},
			"_Test Account Excise Duty @ 15 - _TC": {"_Test Account Excise Duty - _TC": 15},
			"_Test Account Excise Duty @ 20 - _TC": {"_Test Account Excise Duty - _TC": 20},
			"_Test Item Tax Template 1 - _TC": {
				"_Test Account Excise Duty - _TC": 5,
				"_Test Account Education Cess - _TC": 10,
				"_Test Account S&H Education Cess - _TC": 15,
			},
		}

		for data in expected_item_tax_template:
			details = get_item_details(
				{
					"item_code": data["item_code"],
					"tax_category": data["tax_category"],
					"company": "_Test Company",
					"price_list": "_Test Price List",
					"currency": "_Test Currency",
					"doctype": "Sales Order",
					"conversion_rate": 1,
					"price_list_currency": "_Test Currency",
					"plc_conversion_rate": 1,
					"order_type": "Sales",
					"customer": "_Test Customer",
					"conversion_factor": 1,
					"price_list_uom_dependant": 1,
					"ignore_pricing_rule": 1,
				}
			)

			if details.item_tax_template:
				self.assertEqual(details.item_tax_template, data["item_tax_template"])
				self.assertEqual(
					json.loads(details.item_tax_rate), expected_item_tax_map[details.item_tax_template]
				)

	def test_item_defaults(self):
		frappe.delete_doc_if_exists("Item", "Test Item With Defaults", force=1)
		make_item(
			"Test Item With Defaults",
			{
				"item_group": "_Test Item Group",
				"brand": "_Test Brand With Item Defaults",
				"item_defaults": [
					{
						"company": "_Test Company",
						"default_warehouse": "_Test Warehouse 2 - _TC",  # no override
						"expense_account": "_Test Account Stock Expenses - _TC",  # override brand default
						"buying_cost_center": "_Test Write Off Cost Center - _TC",  # override item group default
					}
				],
			},
		)

		sales_item_check = {
			"item_code": "Test Item With Defaults",
			"warehouse": "_Test Warehouse 2 - _TC",  # from item
			"income_account": "_Test Account Sales - _TC",  # from brand
			"expense_account": "_Test Account Stock Expenses - _TC",  # from item
			"cost_center": "_Test Cost Center 2 - _TC",  # from item group
		}
		sales_item_details = get_item_details(
			{
				"item_code": "Test Item With Defaults",
				"company": "_Test Company",
				"price_list": "_Test Price List",
				"currency": "_Test Currency",
				"doctype": "Sales Invoice",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"customer": "_Test Customer",
			}
		)
		for key, value in sales_item_check.items():
			self.assertEqual(value, sales_item_details.get(key))

		purchase_item_check = {
			"item_code": "Test Item With Defaults",
			"warehouse": "_Test Warehouse 2 - _TC",  # from item
			"expense_account": "_Test Account Stock Expenses - _TC",  # from item
			"income_account": "_Test Account Sales - _TC",  # from brand
			"cost_center": "_Test Write Off Cost Center - _TC",  # from item
		}
		purchase_item_details = get_item_details(
			{
				"item_code": "Test Item With Defaults",
				"company": "_Test Company",
				"price_list": "_Test Price List",
				"currency": "_Test Currency",
				"doctype": "Purchase Invoice",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"supplier": "_Test Supplier",
			}
		)
		for key, value in purchase_item_check.items():
			self.assertEqual(value, purchase_item_details.get(key))

	def test_item_default_validations(self):
		with self.assertRaises(frappe.ValidationError) as ve:
			make_item(
				"Bad Item defaults",
				{
					"item_group": "_Test Item Group",
					"item_defaults": [
						{
							"company": "_Test Company 1",
							"default_warehouse": "_Test Warehouse - _TC",
							"expense_account": "Stock In Hand - _TC",
							"buying_cost_center": "_Test Cost Center - _TC",
							"selling_cost_center": "_Test Cost Center - _TC",
						}
					],
				},
			)

		self.assertTrue(
			"belong to company" in str(ve.exception).lower(),
			msg="Mismatching company entities in item defaults should not be allowed.",
		)

	def test_item_attribute_change_after_variant(self):
		frappe.delete_doc_if_exists("Item", "_Test Variant Item-L", force=1)

		variant = create_variant("_Test Variant Item", {"Test Size": "Large"})
		variant.save()

		attribute = frappe.get_doc("Item Attribute", "Test Size")
		attribute.item_attribute_values = []

		# reset flags
		frappe.flags.attribute_values = None

		self.assertRaises(InvalidItemAttributeValueError, attribute.save)
		frappe.db.rollback()

	def test_make_item_variant(self):
		frappe.delete_doc_if_exists("Item", "_Test Variant Item-L", force=1)

		variant = create_variant("_Test Variant Item", {"Test Size": "Large"})
		variant.save()

		# doing it again should raise error
		variant = create_variant("_Test Variant Item", {"Test Size": "Large"})
		variant.item_code = "_Test Variant Item-L-duplicate"
		self.assertRaises(ItemVariantExistsError, variant.save)

	def test_copy_fields_from_template_to_variants(self):
		frappe.delete_doc_if_exists("Item", "_Test Variant Item-XL", force=1)

		fields = [{"field_name": "item_group"}, {"field_name": "is_stock_item"}]
		allow_fields = [d.get("field_name") for d in fields]
		set_item_variant_settings(fields)

		if not frappe.db.get_value(
			"Item Attribute Value", {"parent": "Test Size", "attribute_value": "Extra Large"}, "name"
		):
			item_attribute = frappe.get_doc("Item Attribute", "Test Size")
			item_attribute.append("item_attribute_values", {"attribute_value": "Extra Large", "abbr": "XL"})
			item_attribute.save()

		template = frappe.get_doc("Item", "_Test Variant Item")
		template.item_group = "_Test Item Group D"
		template.save()

		variant = create_variant("_Test Variant Item", {"Test Size": "Extra Large"})
		variant.item_code = "_Test Variant Item-XL"
		variant.item_name = "_Test Variant Item-XL"
		variant.save()

		variant = frappe.get_doc("Item", "_Test Variant Item-XL")
		for fieldname in allow_fields:
			self.assertEqual(template.get(fieldname), variant.get(fieldname))

		template = frappe.get_doc("Item", "_Test Variant Item")
		template.item_group = "_Test Item Group Desktops"
		template.save()

	def test_make_item_variant_with_numeric_values(self):
		# cleanup
		for d in frappe.db.get_all("Item", filters={"variant_of": "_Test Numeric Template Item"}):
			frappe.delete_doc_if_exists("Item", d.name)

		frappe.delete_doc_if_exists("Item", "_Test Numeric Template Item")
		frappe.delete_doc_if_exists("Item Attribute", "Test Item Length")

		frappe.db.sql(
			"""delete from `tabItem Variant Attribute`
			where attribute='Test Item Length' """
		)

		frappe.flags.attribute_values = None

		# make item attribute
		frappe.get_doc(
			{
				"doctype": "Item Attribute",
				"attribute_name": "Test Item Length",
				"numeric_values": 1,
				"from_range": 0.0,
				"to_range": 100.0,
				"increment": 0.5,
			}
		).insert()

		# make template item
		make_item(
			"_Test Numeric Template Item",
			{
				"attributes": [
					{"attribute": "Test Size"},
					{
						"attribute": "Test Item Length",
						"numeric_values": 1,
						"from_range": 0.0,
						"to_range": 100.0,
						"increment": 0.5,
					},
				],
				"item_defaults": [{"default_warehouse": "_Test Warehouse - _TC", "company": "_Test Company"}],
				"has_variants": 1,
			},
		)

		variant = create_variant(
			"_Test Numeric Template Item", {"Test Size": "Large", "Test Item Length": 1.1}
		)
		self.assertEqual(variant.item_code, "_Test Numeric Template Item-L-1.1")
		variant.item_code = "_Test Numeric Variant-L-1.1"
		variant.item_name = "_Test Numeric Variant Large 1.1m"
		self.assertRaises(InvalidItemAttributeValueError, variant.save)

		variant = create_variant(
			"_Test Numeric Template Item", {"Test Size": "Large", "Test Item Length": 1.5}
		)
		self.assertEqual(variant.item_code, "_Test Numeric Template Item-L-1.5")
		variant.item_code = "_Test Numeric Variant-L-1.5"
		variant.item_name = "_Test Numeric Variant Large 1.5m"
		variant.save()

	def test_item_merging(self):
		old = create_item(frappe.generate_hash(length=20)).name
		new = create_item(frappe.generate_hash(length=20)).name

		make_stock_entry(item_code=old, target="_Test Warehouse - _TC", qty=1, rate=100)
		make_stock_entry(item_code=old, target="_Test Warehouse 1 - _TC", qty=1, rate=100)
		make_stock_entry(item_code=new, target="_Test Warehouse 1 - _TC", qty=1, rate=100)

		frappe.rename_doc("Item", old, new, merge=True)

		self.assertFalse(frappe.db.exists("Item", old))

		self.assertTrue(frappe.db.get_value("Bin", {"item_code": new, "warehouse": "_Test Warehouse - _TC"}))
		self.assertTrue(
			frappe.db.get_value("Bin", {"item_code": new, "warehouse": "_Test Warehouse 1 - _TC"})
		)

	def test_item_merging_with_product_bundle(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle

		create_item("Test Item Bundle Item 1", is_stock_item=False)
		create_item("Test Item Bundle Item 2", is_stock_item=False)
		create_item("Test Item inside Bundle")
		bundle_items = ["Test Item inside Bundle"]

		# make bundles for both items
		bundle1 = make_product_bundle("Test Item Bundle Item 1", bundle_items, qty=2)
		make_product_bundle("Test Item Bundle Item 2", bundle_items, qty=2)

		with self.assertRaises(DataValidationError):
			frappe.rename_doc("Item", "Test Item Bundle Item 1", "Test Item Bundle Item 2", merge=True)

		bundle1.delete()
		frappe.rename_doc("Item", "Test Item Bundle Item 1", "Test Item Bundle Item 2", merge=True)

		self.assertFalse(frappe.db.exists("Item", "Test Item Bundle Item 1"))

	def test_uom_conversion_factor(self):
		if frappe.db.exists("Item", "Test Item UOM"):
			frappe.delete_doc("Item", "Test Item UOM")

		item_doc = make_item(
			"Test Item UOM", {"stock_uom": "Gram", "uoms": [dict(uom="Carat"), dict(uom="Kg")]}
		)

		for d in item_doc.uoms:
			value = get_uom_conv_factor(d.uom, item_doc.stock_uom)
			d.conversion_factor = value

		self.assertEqual(item_doc.uoms[0].uom, "Carat")
		self.assertEqual(item_doc.uoms[0].conversion_factor, 0.2)
		self.assertEqual(item_doc.uoms[1].uom, "Kg")
		self.assertEqual(item_doc.uoms[1].conversion_factor, 1000)

	def test_uom_conv_intermediate(self):
		factor = get_uom_conv_factor("Pound", "Gram")
		self.assertAlmostEqual(factor, 453.592, 3)

	def test_uom_conv_base_case(self):
		factor = get_uom_conv_factor("m", "m")
		self.assertEqual(factor, 1.0)

	def test_item_variant_by_manufacturer(self):
		template = make_item(
			"_Test Item Variant By Manufacturer", {"has_variants": 1, "variant_based_on": "Manufacturer"}
		).name

		for manufacturer in ["DFSS", "DASA", "ASAAS"]:
			if not frappe.db.exists("Manufacturer", manufacturer):
				m_doc = frappe.new_doc("Manufacturer")
				m_doc.short_name = manufacturer
				m_doc.insert()

		self.assertFalse(frappe.db.exists("Item Manufacturer", {"manufacturer": "DFSS"}))
		variant = get_variant(template, manufacturer="DFSS", manufacturer_part_no="DFSS-123")

		item_manufacturer = frappe.db.exists(
			"Item Manufacturer", {"manufacturer": "DFSS", "item_code": variant.name}
		)
		self.assertTrue(item_manufacturer)

		frappe.delete_doc("Item Manufacturer", item_manufacturer)

	def test_stock_exists_against_template_item(self):
		stock_item = frappe.get_all("Stock Ledger Entry", fields=["item_code"], limit=1)
		if stock_item:
			item_code = stock_item[0].item_code

			item_doc = frappe.get_doc("Item", item_code)
			item_doc.has_variants = 1
			self.assertRaises(StockExistsForTemplate, item_doc.save)

	def test_add_item_barcode(self):
		# Clean up
		frappe.db.sql("""delete from `tabItem Barcode`""")
		item_code = "Test Item Barcode"
		if frappe.db.exists("Item", item_code):
			frappe.delete_doc("Item", item_code)

		# Create new item and add barcodes
		barcode_properties_list = [
			{"barcode": "0012345678905", "barcode_type": "EAN"},
			{"barcode": "012345678905", "barcode_type": "UAN"},
			{
				"barcode": "ARBITRARY_TEXT",
			},
			{"barcode": "72527273070", "barcode_type": "UPC-A"},
			{"barcode": "123456", "barcode_type": "CODE-39"},
			{"barcode": "401268452363", "barcode_type": "EAN"},
			{"barcode": "90311017", "barcode_type": "EAN"},
			{"barcode": "73513537", "barcode_type": "EAN"},
			{"barcode": "0123456789012", "barcode_type": "GS1"},
			{"barcode": "2211564566668", "barcode_type": "GTIN"},
			{"barcode": "0256480249", "barcode_type": "ISBN"},
			{"barcode": "0192552570", "barcode_type": "ISBN-10"},
			{"barcode": "9781234567897", "barcode_type": "ISBN-13"},
			{"barcode": "9771234567898", "barcode_type": "ISSN"},
			{"barcode": "4581171967072", "barcode_type": "JAN"},
			{"barcode": "12345678", "barcode_type": "PZN"},
			{"barcode": "725272730706", "barcode_type": "UPC"},
		]
		create_item(item_code)
		for barcode_properties in barcode_properties_list:
			item_doc = frappe.get_doc("Item", item_code)
			new_barcode = item_doc.append("barcodes")
			new_barcode.update(barcode_properties)
			item_doc.save()

		# Check values saved correctly
		barcodes = frappe.get_all(
			"Item Barcode", fields=["barcode", "barcode_type"], filters={"parent": item_code}
		)

		for barcode_properties in barcode_properties_list:
			barcode_to_find = barcode_properties["barcode"]
			matching_barcodes = [x for x in barcodes if x["barcode"] == barcode_to_find]
		self.assertEqual(len(matching_barcodes), 1)
		details = matching_barcodes[0]

		for key, value in barcode_properties.items():
			self.assertEqual(value, details.get(key))

		# Add barcode again - should cause DuplicateEntryError
		item_doc = frappe.get_doc("Item", item_code)
		new_barcode = item_doc.append("barcodes")
		new_barcode.update(barcode_properties_list[0])
		self.assertRaises(frappe.DuplicateEntryError, item_doc.save)

		# Add invalid barcode - should cause InvalidBarcode
		item_doc = frappe.get_doc("Item", item_code)
		new_barcode = item_doc.append("barcodes")
		new_barcode.barcode = "9999999999999"
		new_barcode.barcode_type = "EAN"
		self.assertRaises(InvalidBarcode, item_doc.save)

	def test_heatmap_data(self):
		import time

		data = get_timeline_data("Item", "_Test Item")
		self.assertTrue(isinstance(data, dict))

		now = time.time()
		one_year_ago = now - 366 * 24 * 60 * 60

		for timestamp, count in data.items():
			self.assertIsInstance(timestamp, int)
			self.assertTrue(one_year_ago <= timestamp <= now)
			self.assertIsInstance(count, int)
			self.assertTrue(count >= 0)

	def test_index_creation(self):
		"Check if specific columns have indexes in the database"

		# Query to retrieve all indexed columns for the `tabItem` table (converted to lowercase)
		indices = frappe.db.sql(
			"""
			SELECT
				a.attname AS column_name
			FROM
				pg_index i
			JOIN
				pg_attribute a ON a.attnum = ANY(i.indkey)
			WHERE
				i.indrelid = '"tabItem"'::regclass
		""",
			as_dict=1,
		)

		# Collect indexed columns
		indexed_columns = {index["column_name"] for index in indices}

		# Set of columns we expect to have indexes
		expected_columns = {"item_code", "item_name", "item_group"}

		# Check for missing indexes
		missing_columns = expected_columns - indexed_columns
		if missing_columns:
			self.fail(f"Expected database indexes on these columns: {', '.join(missing_columns)}")

	def test_attribute_completions(self):
		expected_attrs = {"Small", "Extra Small", "Extra Large", "Large", "2XL", "Medium"}

		attrs = get_item_attribute("Test Size")
		received_attrs = {attr.attribute_value for attr in attrs}
		self.assertEqual(received_attrs, expected_attrs)

		attrs = get_item_attribute("Test Size", attribute_value="extra")
		received_attrs = {attr.attribute_value for attr in attrs}
		self.assertEqual(received_attrs, {"Extra Small", "Extra Large"})

	def test_check_stock_uom_with_bin(self):
		# this item has opening stock and stock_uom set in test_records.
		item = frappe.get_doc("Item", "_Test Item")
		item.stock_uom = "Gram"
		self.assertRaises(frappe.ValidationError, item.save)

	def test_check_stock_uom_with_bin_no_sle(self):
		from erpnext.stock.stock_balance import update_bin_qty

		item = create_item("_Item with bin qty")
		item.stock_uom = "Gram"
		item.save()

		update_bin_qty(item.item_code, "_Test Warehouse - _TC", {"reserved_qty": 10})

		item.stock_uom = "Kilometer"
		self.assertRaises(frappe.ValidationError, item.save)

		update_bin_qty(item.item_code, "_Test Warehouse - _TC", {"reserved_qty": 0})

		item.load_from_db()
		item.stock_uom = "Kilometer"
		try:
			item.save()
		except frappe.ValidationError as e:
			self.fail(f"UoM change not allowed even though no SLE / BIN with positive qty exists: {e}")

	def test_erasure_of_old_conversions(self):
		item = create_item("_item change uom")
		item.stock_uom = "Gram"
		item.append("uoms", frappe._dict(uom="Box", conversion_factor=2))
		item.save()
		item.reload()
		item.stock_uom = "Nos"
		item.save()
		self.assertEqual(len(item.uoms), 1)

	def test_validate_stock_item(self):
		self.assertRaises(frappe.ValidationError, validate_is_stock_item, "_Test Non Stock Item")

		try:
			validate_is_stock_item("_Test Item")
		except frappe.ValidationError as e:
			self.fail(f"stock item considered non-stock item: {e}")

	@change_settings("Stock Settings", {"item_naming_by": "Naming Series"})
	def test_autoname_series(self):
		item = frappe.new_doc("Item")
		item.item_group = "All Item Groups"
		item.save()  # if item code saved without item_code then series worked

	@change_settings("Stock Settings", {"allow_negative_stock": 0})
	def test_item_wise_negative_stock(self):
		"""When global settings are disabled check that item that allows
		negative stock can still consume material in all known stock
		transactions that consume inventory."""
		from erpnext.stock.stock_ledger import is_negative_stock_allowed

		item = make_item("_TestNegativeItemSetting", {"allow_negative_stock": 1, "valuation_rate": 100})
		self.assertTrue(is_negative_stock_allowed(item_code=item.name))

		self.consume_item_code_with_differet_stock_transactions(item_code=item.name)

	@change_settings("Stock Settings", {"allow_negative_stock": 0})
	def test_backdated_negative_stock(self):
		"""same as test above but backdated entries"""
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item("_TestNegativeItemSetting", {"allow_negative_stock": 1, "valuation_rate": 100})

		# create a future entry so all new entries are backdated
		make_stock_entry(
			qty=1, item_code=item.name, target="_Test Warehouse - _TC", posting_date=add_days(today(), 5)
		)
		self.consume_item_code_with_differet_stock_transactions(item_code=item.name)

	@change_settings("Stock Settings", {"sample_retention_warehouse": "_Test Warehouse - _TC"})
	def test_retain_sample(self):
		item = make_item("_TestRetainSample", {"has_batch_no": 1, "retain_sample": 1, "sample_quantity": 1})

		self.assertEqual(item.has_batch_no, 1)
		self.assertEqual(item.retain_sample, 1)
		self.assertEqual(item.sample_quantity, 1)

		item.has_batch_no = None
		item.save()
		self.assertEqual(item.retain_sample, False)
		self.assertEqual(item.sample_quantity, 0)
		item.delete()

	def consume_item_code_with_differet_stock_transactions(
		self, item_code, warehouse="_Test Warehouse - _TC"
	):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		typical_args = {"item_code": item_code, "warehouse": warehouse}

		create_delivery_note(**typical_args)
		create_sales_invoice(update_stock=1, **typical_args)
		make_stock_entry(item_code=item_code, source=warehouse, qty=1, purpose="Material Issue")
		make_stock_entry(item_code=item_code, source=warehouse, target="Stores - _TC", qty=1)
		# standalone return
		make_purchase_receipt(is_return=True, qty=-1, **typical_args)

	def test_item_dashboard(self):
		from erpnext.stock.dashboard.item_dashboard import get_data

		self.assertTrue(get_data(item_code="_Test Item"))
		self.assertTrue(get_data(warehouse="_Test Warehouse - _TC"))
		self.assertTrue(get_data(item_group="All Item Groups"))

	def test_empty_description(self):
		item = make_item(properties={"description": "<p></p>"})
		self.assertEqual(item.description, item.item_name)
		item.description = ""
		item.save()
		self.assertEqual(item.description, item.item_name)

	def test_item_type_field_change(self):
		"""Check if critical fields like `is_stock_item`, `has_batch_no` are not changed if transactions exist."""
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		transaction_creators = [
			lambda i: make_purchase_receipt(item_code=i),
			lambda i: make_purchase_invoice(item_code=i, update_stock=1),
			lambda i: make_stock_entry(item_code=i, qty=1, target="_Test Warehouse - _TC"),
			lambda i: create_delivery_note(item_code=i),
		]

		properties = {"has_batch_no": 0, "allow_negative_stock": 1, "valuation_rate": 10}
		for transaction_creator in transaction_creators:
			item = make_item(properties=properties)
			transaction = transaction_creator(item.name)
			item.has_batch_no = 1
			self.assertRaises(frappe.ValidationError, item.save)

			transaction.cancel()
			# should be allowed now
			item.reload()
			item.has_batch_no = 1
			item.save()

	def test_customer_codes_length(self):
		"""Check if item code with special characters are allowed."""
		item = make_item(properties={"item_code": "Test Item Code With Special Characters"})
		for _row in range(3):
			item.append("customer_items", {"ref_code": frappe.generate_hash("", 120)})
		item.save()
		self.assertTrue(len(item.customer_code) > 140)

	def test_update_is_stock_item(self):
		# Step - 1: Create an Item with Maintain Stock enabled
		item = make_item(properties={"is_stock_item": 1})

		# Step - 2: Disable Maintain Stock
		item.is_stock_item = 0
		item.save()
		item.reload()
		self.assertEqual(item.is_stock_item, 0)

		# Step - 3: Create Product Bundle
		pb = frappe.new_doc("Product Bundle")
		pb.new_item_code = item.name
		pb.flags.ignore_mandatory = True
		pb.save()

		# Step - 4: Try to enable Maintain Stock, should throw a validation error
		item.is_stock_item = 1
		self.assertRaises(frappe.ValidationError, item.save)
		item.reload()

		# Step - 5: Delete Product Bundle
		pb.delete()

		# Step - 6: Again try to enable Maintain Stock
		item.is_stock_item = 1
		item.save()
		item.reload()
		self.assertEqual(item.is_stock_item, 1)

	def test_serach_fields_for_item(self):
		from erpnext.controllers.queries import item_query

		make_property_setter("Item", None, "search_fields", "item_name", "Data", for_doctype="Doctype")

		item = make_item(properties={"item_name": "Test Item", "description": "Test Description"})
		data = item_query("Item", "Test Item", "", 0, 20, filters={"item_name": "Test Item"}, as_dict=True)
		self.assertEqual(data[0].name, item.name)
		self.assertEqual(data[0].item_name, item.item_name)
		self.assertTrue("description" not in data[0])

		make_property_setter(
			"Item", None, "search_fields", "item_name, description", "Data", for_doctype="Doctype"
		)
		data = item_query("Item", "Test Item", "", 0, 20, filters={"item_name": "Test Item"}, as_dict=True)
		self.assertEqual(data[0].name, item.name)
		self.assertEqual(data[0].item_name, item.item_name)
		self.assertEqual(data[0].description, item.description)
		self.assertTrue("description" in data[0])

	def test_group_warehouse_for_reorder_item(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		item_doc = make_item("_Test Group Warehouse For Reorder Item", {"is_stock_item": 1})
		warehouse = create_warehouse("_Test Warehouse - _TC")
		warehouse_doc = frappe.get_doc("Warehouse", warehouse)
		warehouse_doc.db_set("parent_warehouse", "")

		item_doc.append(
			"reorder_levels",
			{
				"warehouse": warehouse,
				"warehouse_reorder_level": 10,
				"warehouse_reorder_qty": 100,
				"material_request_type": "Purchase",
				"warehouse_group": "_Test Warehouse Group - _TC",
			},
		)

		self.assertRaises(frappe.ValidationError, item_doc.save)

	def test_cr_item_TC_SCK_128(self):
		from frappe.utils import random_string

		item_fields1 = {
			"item_name": f"_Test-{random_string(5)}",
			"valuation_rate": 100,
			"has_batch_no": 1,
			"has_expiry_date": 1,
			"shelf_life_in_days": 30,
		}
		item = make_item(item_fields1["item_name"], item_fields1)
		self.assertEqual(item.has_batch_no, 1)
		self.assertEqual(item.has_expiry_date, 1)
		self.assertEqual(item.shelf_life_in_days, 30)

	def test_create_variant_item_TC_SCK_125(self):
		item = make_item(
			"_Test Template Item",
			{
				"variant_based_on": "Item Attribute",
				"attributes": [{"attribute": "Test Size"}],
				"has_variants": 1,
			},
		)
		self.assertEqual(item.item_code, "_Test Template Item")
		self.assertEqual(item.has_variants, 1)
		self.assertEqual(item.attributes[0].attribute, "Test Size")

	def test_auto_reorder_item_TC_SCK_126(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		group_warehouse = frappe.get_doc("Warehouse", create_warehouse("TestGroup"))
		convert_to_group_or_ledger(group_warehouse.name)
		group_warehouse.reload()
		self.assertEqual(group_warehouse.is_group, 1)
		item = make_item(
			"Test Auto Reorder Item",
			{
				"reorder_levels": [
					{
						"warehouse_group": group_warehouse.name,
						"warehouse": create_warehouse(
							"Test Store", {"parent_warehouse": group_warehouse.name}
						),
						"warehouse_reorder_level": 100,
						"warehouse_reorder_qty": 200,
						"material_request_type": "Purchase",
					}
				]
			},
		)
		self.assertEqual(item.reorder_levels[0].warehouse_group, group_warehouse.name)
		self.assertEqual(item.reorder_levels[0].warehouse_reorder_level, 100)
		self.assertEqual(item.reorder_levels[0].warehouse_reorder_qty, 200)
		self.assertEqual(item.reorder_levels[0].material_request_type, "Purchase")

	def test_cr_item_TC_SCK_129(self):
		from frappe.utils import random_string

		item_fields1 = {
			"item_name": f"_Test-{random_string(5)}",
			"valuation_rate": 100,
			"has_serial_no": 1,
			"has_expiry_date": 1,
			"shelf_life_in_days": 30,
		}
		item = make_item(item_fields1["item_name"], item_fields1)
		self.assertEqual(item.has_serial_no, 1)
		self.assertEqual(item.has_expiry_date, 1)
		self.assertEqual(item.shelf_life_in_days, 30)

	def test_cr_item_TC_SCK_130(self):
		from frappe.utils import random_string

		item_fields1 = {
			"item_name": f"_Test-{random_string(5)}",
			"is_stock_item": 0,
			"valuation_rate": 100,
			"shelf_life_in_days": 30,
		}
		item = make_item(item_fields1["item_name"], item_fields1)
		self.assertEqual(item.is_stock_item, 0)
		self.assertEqual(item.shelf_life_in_days, 30)

	def test_create_item_with_opening_stock_TC_SCK_229(self):
		from frappe.utils import random_string

		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		item_fields1 = {
			"item_name": f"_Test-{random_string(5)}",
			"is_stock_item": 1,
			"item_group": "Raw Material",
			"opening_stock": 100,
			"valuation_rate": 200,
			"standard_rate": 300,
			"item_defaults": [
				{
					"company": "_Test Company",
					"default_warehouse": create_warehouse(
						"Stores-test", properties=None, company="_Test Company"
					),
				}
			],
		}
		item = make_item(item_fields1["item_name"], item_fields1)
		self.assertEqual(item.standard_rate, 300)
		self.assertTrue(frappe.db.get_value("Stock Entry Detail", {"item_code": item.name}, "parent"))
		se = frappe.db.get_value("Stock Entry Detail", {"item_code": item.name}, "parent")
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry", {"item_code": item.name, "voucher_no": se}, "actual_qty"
			),
			100,
		)
		self.assertEqual(frappe.db.get_value("Item Price", {"item_code": item.name}, "price_list_rate"), 300)

	def test_item_cr_TC_SCK_153(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		item_fields = {
			"item_name": "Ball point Pen1",
			"is_stock_item": 1,
			"stock_uom": "Box",
			"item_defaults": [
				{
					"company": "_Test Company",
					"default_warehouse": create_warehouse(
						"Stores-test", properties=None, company="_Test Company"
					),
				}
			],
		}
		item = make_item("Ball point Pen1", item_fields)
		self.assertEqual(item.name, "Ball point Pen1")

	def test_item_group_cr_TC_SCK_154(self):
		parent_itm_grp = frappe.new_doc("Item Group")
		parent_itm_grp.item_group_name = "Test Parent Item Group"
		parent_itm_grp.is_group = 1
		parent_itm_grp.insert()
		itm_grp = frappe.new_doc("Item Group")
		itm_grp.item_group_name = "Test Item Group"
		itm_grp.parent_item_group = "Test Parent Item Group"
		itm_grp.insert()
		self.assertEqual(itm_grp.name, "Test Item Group")
		self.assertEqual(itm_grp.parent_item_group, "Test Parent Item Group")

	def tearDown(self):
		# Cleanup created price lists
		if frappe.db.exists("Item Group", "Software"):
			frappe.delete_doc("Item Group", "Software")

	def test_cr_item_alternative_TC_SCK_150(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record

		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		company = "_Test Company"
		item_fields = {
			"item_name": "_Test Item150",
			"is_stock_item": 1,
			"valuation_rate": 500,
			"allow_alternative_item": 1,
		}
		alt_item_fields = {
			"item_name": "_Test Alt Item",
			"is_stock_item": 1,
			"valuation_rate": 500,
			"allow_alternative_item": 1,
		}
		bot_item_fields = {
			"item_name": "_Test Bom Item",
			"is_stock_item": 1,
			"valuation_rate": 500,
		}
		item = make_item("_Test Item150", item_fields)
		alt_item = make_item("_Test Alt Item", alt_item_fields)
		bom_item = make_item("_Test Bom Item", bot_item_fields)

		if not frappe.db.exists(
			"Item Alternative", {"item_code": item.name, "alternative_item_code": alt_item.name}
		):
			alt_1 = frappe.get_doc(
				{
					"doctype": "Item Alternative",
					"item_code": item.name,
					"alternative_item_code": alt_item.name,
					"is_two_way": 1,
				}
			)
			alt_1.insert()

		if not frappe.db.exists(
			"Item Alternative", {"item_code": alt_item.name, "alternative_item_code": item.name}
		):
			alt_2 = frappe.get_doc(
				{
					"doctype": "Item Alternative",
					"item_code": alt_item.name,
					"alternative_item_code": item.name,
					"is_two_way": 1,
				}
			)
			alt_2.insert()

		if not frappe.db.exists("BOM", {"item": item.name}):
			bom = make_bom(
				item=item.name,
				company=company,
				raw_materials=[bom_item.name, alt_item.name],
				is_active=1,
				is_default=1,
				do_not_submit=True,
			)
		self.assertTrue(frappe.db.exists("BOM", bom.name))

		wo = make_wo_order_test_record(
			company=company,
			production_item=item.name,
			bom_no=frappe.get_value("BOM", {"item": bom_item.name}, "name"),
			qty=10,
		)

		wo.reload()
		wo.alternate_item = alt_item.name
		wo.save()
		self.assertEqual(wo.alternate_item, alt_item.name, "Alternative item not found in Work Order")

	@change_settings("Stock Settings", {"valuation_method": "FIFO"})
	def test_default_valuation_method_TC_SCK_180(self):
		expected_valuation_method = "FIFO"
		updated_stock_settings = frappe.get_doc("Stock Settings")
		self.assertEqual(
			updated_stock_settings.valuation_method,
			expected_valuation_method,
			"Valuation method not set correctly in Stock Settings",
		)

	def test_create_stock_entry_with_batch_TC_SCK_155(self):
		from datetime import datetime, timedelta

		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		company = "_Test Company"
		item_fields = {
			"item_name": "_Test Item155",
			"is_stock_item": 1,
			"valuation_rate": 500,
			"has_batch_no": 1,
			"batch_number_series": "BATCH-Item-.####",
			"create_new_batch": 1,
			"has_expiry_date": 1,
			"shelf_life_in_days": 365,
		}
		item = make_item("_Test Item155", item_fields)
		se = make_stock_entry(
			item_code=item.name,
			target=create_warehouse("_Test Stores", company="_Test Company"),
			qty=10,
			purpose="Material Receipt",
		)
		expiry = se.posting_date + timedelta(days=365)
		self.assertEqual(se.docstatus, 1, "Stock Entry not submitted successfully")
		# Fetch batch details
		batch = frappe.get_last_doc("Batch", filters={"item": item.name})
		self.assertIsNotNone(batch, "Batch not created")
		self.assertEqual(str(batch.expiry_date), str(expiry), "Expiry date mismatch in batch")

	def test_cr_item_alternative_TC_SCK_149(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record

		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		company = "_Test Company"
		item_fields = {
			"item_name": "_Test Item",
			"is_stock_item": 1,
			"valuation_rate": 500,
		}
		alt_item_fields = {
			"item_name": "_Test Alt Item",
			"is_stock_item": 1,
			"valuation_rate": 500,
			"allow_alternative_item": 1,
		}
		bot_item_fields = {
			"item_name": "_Test Bom Item",
			"is_stock_item": 1,
			"valuation_rate": 500,
		}
		item = make_item("_Test Item", item_fields)
		alt_item = make_item("_Test Alt Item", alt_item_fields)
		bom_item = make_item("_Test Bom Item", bot_item_fields)

		if not frappe.db.exists("BOM", {"item": item.name}):
			bom = make_bom(
				item=item.name,
				company=company,
				raw_materials=[bom_item.name, alt_item.name],
				is_active=1,
				is_default=1,
				do_not_submit=True,
			)
		self.assertTrue(frappe.db.exists("BOM", bom.name))
		bom = frappe.get_list("BOM", filters={"item": item.name, "is_active": 1}, limit_page_length=1)
		self.assertGreater(len(bom), 0, "BOM not found for the item")

		wo = make_wo_order_test_record(company=company, production_item=item.name, bom_no=bom[0].name, qty=10)

		wo_items = frappe.get_doc("Work Order", wo.name).required_items
		alt_item_found = any(item.item_code == alt_item.name for item in wo_items)
		self.assertTrue(alt_item_found, "Alternative item not found in Work Order")
		wo.reload()

		from frappe.utils import flt

		# Round amounts to avoid float precision issues before submission
		for item in wo.required_items:
			item.amount = flt(item.amount, 9)
			item.rate = flt(item.rate, 9)

		wo.save()  # Save the changes

		wo.submit()

		self.assertTrue(frappe.db.exists("Work Order", wo.name))
		alternate_item_in_wo = next(
			(item.item_code for item in wo_items if item.item_code == alt_item.name), None
		)
		self.assertEqual(alternate_item_in_wo, alt_item.name, "Alternative item not found in Work Order")

	def test_set_valuation_method_for_item_TC_SCK_179(self):
		item_fields = {
			"item_name": "_Test Book Valuation Method",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"valuation_method": "FIFO",
		}
		item = make_item("_Test Book", item_fields)
		self.assertEqual(item.name, "_Test Book")
		self.assertEqual(item.valuation_method, "FIFO")

	def test_validate_customer_provided_part_valuation_rate_TC_SCK_425(self):
		item_fields = {
			"is_stock_item": 1,
			"is_customer_provided_item": 1,
			"is_purchase_item": 0,
			"valuation_rate": 100,
		}
		msg = '"Customer Provided Item" cannot have Valuation Rate'
		with self.assertRaises(frappe.ValidationError) as e:
			make_item("_test_valuation_rate_item", item_fields)

		self.assertIn(msg, str(e.exception))

	def test_validate_customer_provided_part_is_purchase_item_TC_SCK_426(self):
		item_fields = {
			"is_stock_item": 1,
			"is_customer_provided_item": 1,
			"is_purchase_item": 1,
		}
		msg = '"Customer Provided Item" cannot be Purchase Item also'
		with self.assertRaises(frappe.ValidationError) as e:
			make_item("_test_purchase_item", item_fields)

		self.assertIn(msg, str(e.exception))

	def test_validate_set_opening_stock_TC_SCK_427(self):
		item_fields = {
			"is_stock_item": 1,
			"is_customer_provided_item": 0,
			"standard_rate": 0,
			"valuation_rate": 0,
			"has_serial_no": 0,
			"has_batch_no": 0,
			"opening_stock": 1,
		}
		msg = frappe._("Valuation Rate is mandatory if Opening Stock entered")
		with self.assertRaises(frappe.ValidationError) as e:
			make_item("_test_opening_stock_item", item_fields)

		self.assertIn(msg, str(e.exception))

	def test_validate_naming_series_for_dot_TC_SCK_428(self):
		item_fields = {
			"is_stock_item": 1,
			"serial_no_series": "SRS###",
		}

		msg = frappe._("Invalid naming series (. missing) for Serial Number Series")
		with self.assertRaises(frappe.ValidationError) as e:
			make_item("_test_naming_series_item", item_fields)

		self.assertIn(msg, str(e.exception))

	def test_validate_naming_series_for_hash_TC_SCK_429(self):
		item_fields = {
			"is_stock_item": 1,
			"serial_no_series": "SRS. ###",
		}
		msg = frappe._("Invalid naming series (avoid spaces between '.' and '#') for Serial Number Series.")
		with self.assertRaises(frappe.ValidationError) as e:
			make_item("_test_naming_series_item", item_fields)

		self.assertIn(msg, str(e.exception))

	def test_update_bom_item_description_TC_SCK_430(self):
		item = make_item("_test-item-for-bom", {"is_stock_item": 1})
		item.description = "Initial Description"
		item.save()

		bom = frappe.get_doc(
			{
				"doctype": "BOM",
				"item": item.name,
				"quantity": 1,
				"is_active": 1,
				"is_default": 1,
				"items": [{"item_code": item.name, "qty": 1, "rate": 100}],
			}
		)
		bom.insert()
		bom.submit()

		item.reload()
		item.description = "Updated BOM Description"
		item.save()

		item.update_bom_item_desc()

		bom_desc = frappe.db.get_value("BOM", bom.name, "description")
		bom_item_desc = frappe.db.get_value(
			"BOM Item", {"parent": bom.name, "item_code": item.name}, "description"
		)
		explosion_desc = frappe.db.get_value(
			"BOM Explosion Item", {"parent": bom.name, "item_code": item.name}, "description"
		)

		self.assertEqual(bom_desc, "Updated BOM Description")
		self.assertEqual(bom_item_desc, "Updated BOM Description")
		self.assertEqual(explosion_desc, "Updated BOM Description")

	def test_deleted_attribute_in_template_raises_error_TC_SCK_431(self):
		create_attribute("Color", ["Red", "Blue"])
		create_attribute("Size", ["S", "M", "L"])

		template = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_test_variant_attr",
				"item_group": "All Item Groups",
				"has_variants": 1,
				"attributes": [
					{"attribute": "Color", "attribute_value": "Red"},
					{"attribute": "Size", "attribute_value": "M"},
				],
			}
		)
		if "india_compliance" in frappe.get_installed_apps():
			template.gst_hsn_code = get_hsn()
		template.insert(ignore_permissions=True)
		variant = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_test_variant_attr1",
				"item_group": "All Item Groups",
				"variant_of": template.name,
				"attributes": [
					{"attribute": "Color", "attribute_value": "Red"},
					{"attribute": "Size", "attribute_value": "M"},
				],
			}
		)
		if "india_compliance" in frappe.get_installed_apps():
			variant.gst_hsn_code = get_hsn()
		variant.insert(ignore_permissions=True)

		template.reload()
		template.set("attributes", [])
		template.append("attributes", {"attribute": "Color", "attribute_values": ["Red", "Blue"]})
		msg = frappe._("The following deleted attributes exist in Variants but not in the Template.")
		with self.assertRaises(frappe.ValidationError) as cm:
			template.save()
		self.assertIn(msg, str(cm.exception))

	def test_item_autoname_with_naming_series_TC_SCK_432(self):
		frappe.db.set_default("item_naming_by", "Naming Series")
		template = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_test_variant_template",
				"item_name": "Test Variant Template",
				"stock_uom": "Nos",
				"item_group": "All Item Groups",
				"has_variants": 1,
				"attributes": [{"attribute": "Color", "attribute_value": "Red"}],
			}
		)
		if "india_compliance" in frappe.get_installed_apps():
			template.gst_hsn_code = get_hsn()
		template.insert(ignore_permissions=True)

		variant = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "Variant Without Item Code",
				"variant_of": template.name,
				"stock_uom": "Nos",
				"item_group": "All Item Groups",
				"attributes": [{"attribute": "Color", "attribute_value": "Red"}],
			}
		)
		if "india_compliance" in frappe.get_installed_apps():
			template.gst_hsn_code = get_hsn()

		variant.autoname()

		# set name as item code
		self.assertEqual(variant.name, "Variant Without Item Code")

	def test_update_template_tables_TC_SCK_433(self):
		create_tax_accounts()
		frappe.db.set_default("item_naming_by", "Naming Series")

		if not frappe.db.exists("Item Tax Template", "Standard Tax Template - _TC"):
			tax_template = frappe.get_doc(
				{
					"doctype": "Item Tax Template",
					"title": "Standard Tax Template",
					"gst_rate": 18,
					"company": "_Test Company",
					"item_tax_template_name": "Standard Tax Template",
					"taxes": [
						{"tax_type": "CGST - _TC", "tax_rate": 9},
						{"tax_type": "SGST - _TC", "tax_rate": 9},
					],
					"gst_category": "Taxable",
				}
			)
			tax_template.insert(ignore_permissions=True)

		template = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_test_template_tables",
				"item_name": "Template Tables",
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"gst_hsn_code": get_hsn(),
				"has_variants": 1,
				"taxes": [
					{
						"item_tax_template": "Standard Tax Template - _TC",
						"charge_type": "On Net Total",
						"account_head": "CGST - _TC",
						"maximum_net_rate": 9,
					},
				],
				"reorder_levels": [
					{
						"warehouse": "_Test Warehouse - _TC",
						"warehouse_reorder_level": 10,
						"warehouse_reorder_qty": 25,
						"material_request_type": "Purchase",
					}
				],
				"attributes": [{"attribute": "Color", "attribute_value": "Red"}],
			}
		).insert(ignore_permissions=True)

		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_test_update_template_tables",
				"item_name": "Test Copy From Template",
				"variant_of": template.name,
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"gst_hsn_code": get_hsn(),
				"item_tax_template": "Standard Tax Template",
			}
		)

		item.update_template_tables()

		self.assertEqual(len(item.taxes), 1)
		self.assertEqual(item.taxes[0].maximum_net_rate, 9)
		self.assertEqual(len(item.reorder_levels), 1)
		self.assertEqual(item.reorder_levels[0].warehouse_reorder_qty, 25)

	def test_after_rename_with_merge_TC_SCK_434(self):
		old_item = make_item("_test_old_item", {"stock_uom": "Nos"})

		new_item = make_item("_test_new_item", {"stock_uom": "Nos"})
		if not frappe.db.exists("Account", "Test Tax Account - _TC"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Test Tax Account",
					"parent_account": "Duties and Taxes - _TC",  # Change suffix to match your company abbreviation
					"company": "_Test Company",
					"is_group": 0,
					"account_type": "Tax",
				}
			).insert()
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"items": [{"item_code": old_item.name, "qty": 1, "rate": 100}],
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": "Test Tax Account - _TC",
						"description": "Test Tax",
						"item_wise_tax_detail": json.dumps({old_item.name: ["10.0", "INR"]}),
					}
				],
			}
		).insert()

		item_doc = frappe.get_doc("Item", new_item.name)
		item_doc.after_rename(old_item.name, new_item.name, merge=True)

		invoice.reload()
		tax_detail = json.loads(invoice.taxes[0].item_wise_tax_detail)
		assert new_item.name in tax_detail
		assert old_item.name not in tax_detail
		assert frappe.db.get_value("Item", new_item.name, "item_code") == new_item.name

	def test_validate_properties_before_merge_fail_TC_SCK_435(self):
		item_1 = make_item(
			"_test_item_merge_1",
			{"stock_uom": "Nos", "is_stock_item": 1, "has_serial_no": 0, "has_batch_no": 0},
		)
		item_2 = make_item(
			"_test_item_merge_2",
			{"stock_uom": "Box", "is_stock_item": 1, "has_serial_no": 0, "has_batch_no": 0},
		)
		with self.assertRaises(frappe.ValidationError) as e:
			item_1.validate_properties_before_merge(item_2.name)
		self.assertIn("To merge, following properties must be same for both items", str(e.exception))

	def test_validate_duplicate_product_bundles_before_merge_pass_TC_SCK_436(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_1 = make_item("_test_item_bundle_1", {"stock_uom": "Nos", "is_stock_item": 0})
		item_2 = make_item("_test_item_bundle_2", {"stock_uom": "Nos", "is_stock_item": 0})

		frappe.get_doc(
			{
				"doctype": "Product Bundle",
				"new_item_code": item_1.name,
				"items": [{"item_code": item_1.name, "qty": 1}],
			}
		).insert()

		frappe.get_doc(
			{
				"doctype": "Product Bundle",
				"new_item_code": item_2.name,
				"items": [{"item_code": item_2.name, "qty": 1}],
			}
		).insert()
		with self.assertRaises(frappe.ValidationError) as e:
			item_1.validate_duplicate_product_bundles_before_merge(item_1.name, item_2.name)
		self.assertIn("Please delete Product Bundle", str(e.exception))

	def test_update_variants_TC_SCK_437(self):
		from erpnext.stock.doctype.item.item import update_variants

		create_attribute("Color", ["Red", "Blue"])
		create_attribute("Size", ["S", "M", "L"])
		template = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_test_variant_attr" + frappe.generate_hash(length=2),
				"item_group": "All Item Groups",
				"gst_hsn_code": get_hsn(),
				"has_variants": 1,
				"attributes": [
					{"attribute": "Color", "attribute_value": "Red"},
					{"attribute": "Size", "attribute_value": "M"},
				],
			}
		).insert(ignore_permissions=True)

		variant = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_test_variant_attr" + frappe.generate_hash(length=2),
				"item_group": "All Item Groups",
				"gst_hsn_code": get_hsn(),
				"variant_of": template.name,
				"attributes": [
					{"attribute": "Color", "attribute_value": "Red"},
					{"attribute": "Size", "attribute_value": "M"},
				],
			}
		)
		variant.insert(ignore_permissions=True)
		variants = [variant.name]

		update_variants(variants, template, publish_progress=True)

		variant.reload()
		assert variant.stock_uom == template.stock_uom


def set_item_variant_settings(fields):
	doc = frappe.get_doc("Item Variant Settings")
	doc.set("fields", fields)
	doc.save()


def make_item_variant():
	if not frappe.db.exists("Item", "_Test Variant Item-S"):
		variant = create_variant("_Test Variant Item", """{"Test Size": "Small"}""")
		variant.item_code = "_Test Variant Item-S"
		variant.item_name = "_Test Variant Item-S"
		variant.save()


test_records = frappe.get_test_records("Item")


def create_item(
	item_code,
	is_stock_item=1,
	valuation_rate=0,
	stock_uom="Nos",
	warehouse="_Test Warehouse - _TC",
	is_customer_provided_item=None,
	customer=None,
	is_purchase_item=None,
	opening_stock=0,
	is_fixed_asset=0,
	asset_category=None,
	buying_cost_center=None,
	selling_cost_center=None,
	company="_Test Company",
	has_batch_no=0,
):
	if not frappe.db.exists("Item", item_code):
		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_name = item_code
		item.description = item_code
		item.item_group = "All Item Groups"
		item.stock_uom = stock_uom
		item.has_batch_no = has_batch_no
		item.is_stock_item = is_stock_item
		item.is_fixed_asset = is_fixed_asset
		item.asset_category = asset_category
		item.opening_stock = opening_stock
		item.valuation_rate = valuation_rate
		item.is_purchase_item = is_purchase_item
		item.is_customer_provided_item = is_customer_provided_item
		item.customer = customer or ""
		item.append(
			"item_defaults",
			{
				"default_warehouse": warehouse,
				"company": company,
				"selling_cost_center": selling_cost_center,
				"buying_cost_center": buying_cost_center,
			},
		)

		if "india_compliance" in frappe.get_installed_apps():
			gst_hsn_code = "11112222"
			if not frappe.db.exists("GST HSN Code", gst_hsn_code):
				gst_hsn_code = frappe.new_doc("GST HSN Code")
				gst_hsn_code.hsn_code = "11112222"
				gst_hsn_code.save()
				item.gst_hsn_code = gst_hsn_code.hsn_code
			else:
				item.gst_hsn_code = gst_hsn_code
		item.save(ignore_permissions=True)
	else:
		item = frappe.get_doc("Item", item_code)
	return item


def create_attribute(name, values):
	existing = frappe.db.get("Item Attribute", name)
	if existing:
		attr_doc = frappe.get_doc("Item Attribute", name)
		existing_values = {v.attribute_value for v in attr_doc.item_attribute_values}
		existing_abbrs = {v.abbr for v in attr_doc.item_attribute_values if v.abbr}

		for v in values:
			if v not in existing_values:
				abbr = v[:1].upper()
				counter = 1
				while abbr in existing_abbrs:
					abbr = f"{v[:1].upper()}{counter}"
					counter += 1
				attr_doc.append("item_attribute_values", {"attribute_value": v, "abbr": abbr})
				existing_abbrs.add(abbr)
		attr_doc.save()
	else:
		abbrs = set()
		value_rows = []
		for v in values:
			abbr = v[:1].upper()
			counter = 1
			while abbr in abbrs:
				abbr = f"{v[:1].upper()}{counter}"
				counter += 1
			value_rows.append({"attribute_value": v, "abbr": abbr})
			abbrs.add(abbr)

		frappe.get_doc(
			{"doctype": "Item Attribute", "attribute_name": name, "item_attribute_values": value_rows}
		).insert()


def get_hsn(hsn="14455767"):
	if not frappe.db.exists("GST HSN Code", hsn):
		gst_hsn_code = frappe.new_doc("GST HSN Code")
		gst_hsn_code.hsn_code = hsn
		gst_hsn_code.save()
		return gst_hsn_code.name
	else:
		return hsn


def create_tax_accounts():
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

	create_company()
	if not frappe.db.exists("Account", "CGST - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "CGST",
				"company": "_Test Company",
				"parent_account": "Duties and Taxes - _TC",
				"account_type": "Tax",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Account", "SGST - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "SGST",
				"company": "_Test Company",
				"parent_account": "Duties and Taxes - _TC",
				"account_type": "Tax",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

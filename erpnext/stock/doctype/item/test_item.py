# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe.test_runner import make_test_objects

from erpnext.controllers.item_variant import (
	InvalidItemAttributeValueError,
	ItemVariantExistsError,
	create_variant,
	get_variant,
)
from erpnext.stock.doctype.item.item import (
	InvalidBarcode,
	StockExistsForTemplate,
	get_item_attribute,
	get_timeline_data,
	get_uom_conv_factor,
	validate_is_stock_item,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.get_item_details import get_item_details
from erpnext.tests.utils import ERPNextTestCase, change_settings

test_ignore = ["BOM"]
test_dependencies = ["Warehouse", "Item Group", "Item Tax Template", "Brand", "Item Attribute"]

def make_item(item_code, properties=None):
	if frappe.db.exists("Item", item_code):
		return frappe.get_doc("Item", item_code)

	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": item_code,
		"item_name": item_code,
		"description": item_code,
		"item_group": "Products"
	})

	if properties:
		item.update(properties)

	if item.is_stock_item:
		for item_default in [doc for doc in item.get("item_defaults") if not doc.default_warehouse]:
			item_default.default_warehouse = "_Test Warehouse - _TC"
			item_default.company = "_Test Company"
	item.insert()

	return item

class TestItem(ERPNextTestCase):
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
		}

		make_test_objects("Item Price")

		company = "_Test Company"
		currency = frappe.get_cached_value("Company",  company,  "default_currency")

		details = get_item_details({
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
			"ignore_pricing_rule": 1
		})

		for key, value in to_check.items():
			self.assertEqual(value, details.get(key))

	def test_item_tax_template(self):
		expected_item_tax_template = [
			{"item_code": "_Test Item With Item Tax Template", "tax_category": "",
				"item_tax_template": "_Test Account Excise Duty @ 10 - _TC"},
			{"item_code": "_Test Item With Item Tax Template", "tax_category": "_Test Tax Category 1",
				"item_tax_template": "_Test Account Excise Duty @ 12 - _TC"},
			{"item_code": "_Test Item With Item Tax Template", "tax_category": "_Test Tax Category 2",
				"item_tax_template": None},

			{"item_code": "_Test Item Inherit Group Item Tax Template 1", "tax_category": "",
				"item_tax_template": "_Test Account Excise Duty @ 10 - _TC"},
			{"item_code": "_Test Item Inherit Group Item Tax Template 1", "tax_category": "_Test Tax Category 1",
				"item_tax_template": "_Test Account Excise Duty @ 12 - _TC"},
			{"item_code": "_Test Item Inherit Group Item Tax Template 1", "tax_category": "_Test Tax Category 2",
				"item_tax_template": None},

			{"item_code": "_Test Item Inherit Group Item Tax Template 2", "tax_category": "",
				"item_tax_template": "_Test Account Excise Duty @ 15 - _TC"},
			{"item_code": "_Test Item Inherit Group Item Tax Template 2", "tax_category": "_Test Tax Category 1",
				"item_tax_template": "_Test Account Excise Duty @ 12 - _TC"},
			{"item_code": "_Test Item Inherit Group Item Tax Template 2", "tax_category": "_Test Tax Category 2",
				"item_tax_template": None},

			{"item_code": "_Test Item Override Group Item Tax Template", "tax_category": "",
				"item_tax_template": "_Test Account Excise Duty @ 20 - _TC"},
			{"item_code": "_Test Item Override Group Item Tax Template", "tax_category": "_Test Tax Category 1",
				"item_tax_template": "_Test Item Tax Template 1 - _TC"},
			{"item_code": "_Test Item Override Group Item Tax Template", "tax_category": "_Test Tax Category 2",
				"item_tax_template": None},
		]

		expected_item_tax_map = {
			None: {},
			"_Test Account Excise Duty @ 10 - _TC": {"_Test Account Excise Duty - _TC": 10},
			"_Test Account Excise Duty @ 12 - _TC": {"_Test Account Excise Duty - _TC": 12},
			"_Test Account Excise Duty @ 15 - _TC": {"_Test Account Excise Duty - _TC": 15},
			"_Test Account Excise Duty @ 20 - _TC": {"_Test Account Excise Duty - _TC": 20},
			"_Test Item Tax Template 1 - _TC": {"_Test Account Excise Duty - _TC": 5, "_Test Account Education Cess - _TC": 10,
				"_Test Account S&H Education Cess - _TC": 15}
		}

		for data in expected_item_tax_template:
			details = get_item_details({
				"item_code": data['item_code'],
				"tax_category": data['tax_category'],
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
				"ignore_pricing_rule": 1
			})

			self.assertEqual(details.item_tax_template, data['item_tax_template'])
			self.assertEqual(json.loads(details.item_tax_rate), expected_item_tax_map[details.item_tax_template])

	def test_item_defaults(self):
		frappe.delete_doc_if_exists("Item", "Test Item With Defaults", force=1)
		make_item("Test Item With Defaults", {
			"item_group": "_Test Item Group",
			"brand": "_Test Brand With Item Defaults",
			"item_defaults": [{
				"company": "_Test Company",
				"default_warehouse": "_Test Warehouse 2 - _TC",  # no override
				"expense_account": "_Test Account Stock Expenses - _TC",  # override brand default
				"buying_cost_center": "_Test Write Off Cost Center - _TC",  # override item group default
			}]
		})

		sales_item_check = {
			"item_code": "Test Item With Defaults",
			"warehouse": "_Test Warehouse 2 - _TC",  # from item
			"income_account": "_Test Account Sales - _TC",  # from brand
			"expense_account": "_Test Account Stock Expenses - _TC",  # from item
			"cost_center": "_Test Cost Center 2 - _TC",  # from item group
		}
		sales_item_details = get_item_details({
			"item_code": "Test Item With Defaults",
			"company": "_Test Company",
			"price_list": "_Test Price List",
			"currency": "_Test Currency",
			"doctype": "Sales Invoice",
			"conversion_rate": 1,
			"price_list_currency": "_Test Currency",
			"plc_conversion_rate": 1,
			"customer": "_Test Customer",
		})
		for key, value in sales_item_check.items():
			self.assertEqual(value, sales_item_details.get(key))

		purchase_item_check = {
			"item_code": "Test Item With Defaults",
			"warehouse": "_Test Warehouse 2 - _TC",  # from item
			"expense_account": "_Test Account Stock Expenses - _TC",  # from item
			"income_account": "_Test Account Sales - _TC",  # from brand
			"cost_center": "_Test Write Off Cost Center - _TC"  # from item
		}
		purchase_item_details = get_item_details({
			"item_code": "Test Item With Defaults",
			"company": "_Test Company",
			"price_list": "_Test Price List",
			"currency": "_Test Currency",
			"doctype": "Purchase Invoice",
			"conversion_rate": 1,
			"price_list_currency": "_Test Currency",
			"plc_conversion_rate": 1,
			"supplier": "_Test Supplier",
		})
		for key, value in purchase_item_check.items():
			self.assertEqual(value, purchase_item_details.get(key))

	def test_item_default_validations(self):

		with self.assertRaises(frappe.ValidationError) as ve:
			make_item("Bad Item defaults", {
				"item_group": "_Test Item Group",
				"item_defaults": [{
					"company": "_Test Company 1",
					"default_warehouse": "_Test Warehouse - _TC",
					"expense_account": "Stock In Hand - _TC",
					"buying_cost_center": "_Test Cost Center - _TC",
					"selling_cost_center": "_Test Cost Center - _TC",
				}]
			})

		self.assertTrue("belong to company" in str(ve.exception).lower(),
				msg="Mismatching company entities in item defaults should not be allowed.")

	def test_item_attribute_change_after_variant(self):
		frappe.delete_doc_if_exists("Item", "_Test Variant Item-L", force=1)

		variant = create_variant("_Test Variant Item", {"Test Size": "Large"})
		variant.save()

		attribute = frappe.get_doc('Item Attribute', 'Test Size')
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

		fields = [{'field_name': 'item_group'}, {'field_name': 'is_stock_item'}]
		allow_fields = [d.get('field_name') for d in fields]
		set_item_variant_settings(fields)

		if not frappe.db.get_value('Item Attribute Value',
			{'parent': 'Test Size', 'attribute_value': 'Extra Large'}, 'name'):
			item_attribute = frappe.get_doc('Item Attribute', 'Test Size')
			item_attribute.append('item_attribute_values', {
				'attribute_value' : 'Extra Large',
				'abbr': 'XL'
			})
			item_attribute.save()

		template = frappe.get_doc('Item', '_Test Variant Item')
		template.item_group = "_Test Item Group D"
		template.save()

		variant = create_variant("_Test Variant Item", {"Test Size": "Extra Large"})
		variant.item_code = "_Test Variant Item-XL"
		variant.item_name = "_Test Variant Item-XL"
		variant.save()

		variant = frappe.get_doc('Item', '_Test Variant Item-XL')
		for fieldname in allow_fields:
			self.assertEqual(template.get(fieldname), variant.get(fieldname))

		template = frappe.get_doc('Item', '_Test Variant Item')
		template.item_group = "_Test Item Group Desktops"
		template.save()

	def test_make_item_variant_with_numeric_values(self):
		# cleanup
		for d in frappe.db.get_all('Item', filters={'variant_of':
				'_Test Numeric Template Item'}):
			frappe.delete_doc_if_exists("Item", d.name)

		frappe.delete_doc_if_exists("Item", "_Test Numeric Template Item")
		frappe.delete_doc_if_exists("Item Attribute", "Test Item Length")

		frappe.db.sql('''delete from `tabItem Variant Attribute`
			where attribute="Test Item Length"''')

		frappe.flags.attribute_values = None

		# make item attribute
		frappe.get_doc({
			"doctype": "Item Attribute",
			"attribute_name": "Test Item Length",
			"numeric_values": 1,
			"from_range": 0.0,
			"to_range": 100.0,
			"increment": 0.5
		}).insert()

		# make template item
		make_item("_Test Numeric Template Item", {
			"attributes": [
				{
					"attribute": "Test Size"
				},
				{
					"attribute": "Test Item Length",
					"numeric_values": 1,
					"from_range": 0.0,
					"to_range": 100.0,
					"increment": 0.5
				}
			],
			"item_defaults": [
				{
					"default_warehouse": "_Test Warehouse - _TC",
					"company": "_Test Company"
				}
			],
			"has_variants": 1
		})

		variant = create_variant("_Test Numeric Template Item",
			{"Test Size": "Large", "Test Item Length": 1.1})
		self.assertEqual(variant.item_code, "_Test Numeric Template Item-L-1.1")
		variant.item_code = "_Test Numeric Variant-L-1.1"
		variant.item_name = "_Test Numeric Variant Large 1.1m"
		self.assertRaises(InvalidItemAttributeValueError, variant.save)

		variant = create_variant("_Test Numeric Template Item",
			{"Test Size": "Large", "Test Item Length": 1.5})
		self.assertEqual(variant.item_code, "_Test Numeric Template Item-L-1.5")
		variant.item_code = "_Test Numeric Variant-L-1.5"
		variant.item_name = "_Test Numeric Variant Large 1.5m"
		variant.save()

	def test_item_merging(self):
		create_item("Test Item for Merging 1")
		create_item("Test Item for Merging 2")

		make_stock_entry(item_code="Test Item for Merging 1", target="_Test Warehouse - _TC",
			qty=1, rate=100)
		make_stock_entry(item_code="Test Item for Merging 2", target="_Test Warehouse 1 - _TC",
			qty=1, rate=100)

		frappe.rename_doc("Item", "Test Item for Merging 1", "Test Item for Merging 2", merge=True)

		self.assertFalse(frappe.db.exists("Item", "Test Item for Merging 1"))

		self.assertTrue(frappe.db.get_value("Bin",
			{"item_code": "Test Item for Merging 2", "warehouse": "_Test Warehouse - _TC"}))

		self.assertTrue(frappe.db.get_value("Bin",
			{"item_code": "Test Item for Merging 2", "warehouse": "_Test Warehouse 1 - _TC"}))

	def test_uom_conversion_factor(self):
		if frappe.db.exists('Item', 'Test Item UOM'):
			frappe.delete_doc('Item', 'Test Item UOM')

		item_doc = make_item("Test Item UOM", {
			"stock_uom": "Gram",
			"uoms": [dict(uom='Carat'), dict(uom='Kg')]
		})

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
		fields = [{'field_name': 'description'}, {'field_name': 'variant_based_on'}]
		set_item_variant_settings(fields)

		if frappe.db.exists('Item', '_Test Variant Mfg'):
			frappe.delete_doc('Item', '_Test Variant Mfg')
		if frappe.db.exists('Item', '_Test Variant Mfg-1'):
			frappe.delete_doc('Item', '_Test Variant Mfg-1')
		if frappe.db.exists('Manufacturer', 'MSG1'):
			frappe.delete_doc('Manufacturer', 'MSG1')

		template = frappe.get_doc(dict(
			doctype='Item',
			item_code='_Test Variant Mfg',
			has_variant=1,
			item_group='Products',
			variant_based_on='Manufacturer'
		)).insert()

		manufacturer = frappe.get_doc(dict(
			doctype='Manufacturer',
			short_name='MSG1'
		)).insert()

		variant = get_variant(template.name, manufacturer=manufacturer.name)
		self.assertEqual(variant.item_code, '_Test Variant Mfg-1')
		self.assertEqual(variant.description, '_Test Variant Mfg')
		self.assertEqual(variant.manufacturer, 'MSG1')
		variant.insert()

		variant = get_variant(template.name, manufacturer=manufacturer.name,
			manufacturer_part_no='007')
		self.assertEqual(variant.item_code, '_Test Variant Mfg-2')
		self.assertEqual(variant.description, '_Test Variant Mfg')
		self.assertEqual(variant.manufacturer, 'MSG1')
		self.assertEqual(variant.manufacturer_part_no, '007')

	def test_stock_exists_against_template_item(self):
		stock_item = frappe.get_all('Stock Ledger Entry', fields = ["item_code"], limit=1)
		if stock_item:
			item_code = stock_item[0].item_code

			item_doc = frappe.get_doc('Item', item_code)
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
			{
				"barcode": "0012345678905",
				"barcode_type": "EAN"
			},
			{
				"barcode": "012345678905",
				"barcode_type": "UAN"
			},
			{
				"barcode": "ARBITRARY_TEXT",
			}
		]
		create_item(item_code)
		for barcode_properties in barcode_properties_list:
			item_doc = frappe.get_doc('Item', item_code)
			new_barcode = item_doc.append('barcodes')
			new_barcode.update(barcode_properties)
			item_doc.save()

		# Check values saved correctly
		barcodes = frappe.get_list(
			'Item Barcode',
			fields=['barcode', 'barcode_type'],
			filters={'parent': item_code})

		for barcode_properties in barcode_properties_list:
			barcode_to_find = barcode_properties['barcode']
			matching_barcodes = [
				x for x in barcodes
				if x['barcode'] == barcode_to_find
			]
		self.assertEqual(len(matching_barcodes), 1)
		details = matching_barcodes[0]

		for key, value in barcode_properties.items():
			self.assertEqual(value, details.get(key))

		# Add barcode again - should cause DuplicateEntryError
		item_doc = frappe.get_doc('Item', item_code)
		new_barcode = item_doc.append('barcodes')
		new_barcode.update(barcode_properties_list[0])
		self.assertRaises(frappe.UniqueValidationError, item_doc.save)

		# Add invalid barcode - should cause InvalidBarcode
		item_doc = frappe.get_doc('Item', item_code)
		new_barcode = item_doc.append('barcodes')
		new_barcode.barcode = '9999999999999'
		new_barcode.barcode_type = 'EAN'
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
		"check if index is getting created in db"
		from erpnext.stock.doctype.item.item import on_doctype_update
		on_doctype_update()

		indices = frappe.db.sql("show index from tabItem", as_dict=1)
		expected_columns = {"item_code", "item_name", "item_group", "route"}
		for index in indices:
			expected_columns.discard(index.get("Column_name"))

		if expected_columns:
			self.fail(f"Expected db index on these columns: {', '.join(expected_columns)}")

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

		update_bin_qty(item.item_code, "_Test Warehouse - _TC", {
			"reserved_qty": 10
		})

		item.stock_uom = "Kilometer"
		self.assertRaises(frappe.ValidationError, item.save)

		update_bin_qty(item.item_code, "_Test Warehouse - _TC", {
			"reserved_qty": 0
		})

		item.load_from_db()
		item.stock_uom = "Kilometer"
		try:
			item.save()
		except frappe.ValidationError as e:
			self.fail(f"UoM change not allowed even though no SLE / BIN with positive qty exists: {e}")

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


def set_item_variant_settings(fields):
	doc = frappe.get_doc('Item Variant Settings')
	doc.set('fields', fields)
	doc.save()

def make_item_variant():
	if not frappe.db.exists("Item", "_Test Variant Item-S"):
		variant = create_variant("_Test Variant Item", """{"Test Size": "Small"}""")
		variant.item_code = "_Test Variant Item-S"
		variant.item_name = "_Test Variant Item-S"
		variant.save()

test_records = frappe.get_test_records('Item')

def create_item(item_code, is_stock_item=1, valuation_rate=0, warehouse="_Test Warehouse - _TC",
		is_customer_provided_item=None, customer=None, is_purchase_item=None, opening_stock=0, is_fixed_asset=0,
		asset_category=None, company="_Test Company"):
	if not frappe.db.exists("Item", item_code):
		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_name = item_code
		item.description = item_code
		item.item_group = "All Item Groups"
		item.is_stock_item = is_stock_item
		item.is_fixed_asset = is_fixed_asset
		item.asset_category = asset_category
		item.opening_stock = opening_stock
		item.valuation_rate = valuation_rate
		item.is_purchase_item = is_purchase_item
		item.is_customer_provided_item = is_customer_provided_item
		item.customer = customer or ''
		item.append("item_defaults", {
			"default_warehouse": warehouse,
			"company": company
		})
		item.save()
	else:
		item = frappe.get_doc("Item", item_code)
	return item

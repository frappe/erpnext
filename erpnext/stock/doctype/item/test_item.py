# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe

from frappe.test_runner import make_test_records
from erpnext.controllers.item_variant import (create_variant, ItemVariantExistsError,
	InvalidItemAttributeValueError, get_variant)

from frappe.model.rename_doc import rename_doc
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

test_ignore = ["BOM"]
test_dependencies = ["Warehouse"]

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


	if item.is_stock_item and not item.default_warehouse:
		item.default_warehouse = "_Test Warehouse - _TC"

	item.insert()

	return item

class TestItem(unittest.TestCase):
	def setUp(self):
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
		from erpnext.stock.get_item_details import get_item_details
		to_check = {
			"item_code": "_Test Item",
			"item_name": "_Test Item",
			"description": "_Test Item 1",
			"warehouse": "_Test Warehouse - _TC",
			"income_account": "Sales - _TC",
			"expense_account": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center 2 - _TC",
			"qty": 1.0,
			"price_list_rate": 100.0,
			"base_price_list_rate": 0.0,
			"discount_percentage": 0.0,
			"rate": 0.0,
			"base_rate": 0.0,
			"amount": 0.0,
			"base_amount": 0.0,
			"batch_no": None,
			"item_tax_rate": '{}',
			"uom": "_Test UOM",
			"conversion_factor": 1.0,
		}

		make_test_records("Item Price")

		details = get_item_details({
			"item_code": "_Test Item",
			"company": "_Test Company",
			"price_list": "_Test Price List",
			"currency": "_Test Currency",
			"doctype": "Sales Order",
			"conversion_rate": 1,
			"price_list_currency": "_Test Currency",
			"plc_conversion_rate": 1,
			"order_type": "Sales",
			"customer": "_Test Customer"
		})

		for key, value in to_check.iteritems():
			self.assertEquals(value, details.get(key))

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
			"default_warehouse": "_Test Warehouse - _TC"
		})

		variant = create_variant("_Test Numeric Template Item",
			{"Test Size": "Large", "Test Item Length": 1.1})
		self.assertEquals(variant.item_code, "_Test Numeric Template Item-L-1.1")
		variant.item_code = "_Test Numeric Variant-L-1.1"
		variant.item_name = "_Test Numeric Variant Large 1.1m"
		self.assertRaises(InvalidItemAttributeValueError, variant.save)

		variant = create_variant("_Test Numeric Template Item",
			{"Test Size": "Large", "Test Item Length": 1.5})
		self.assertEquals(variant.item_code, "_Test Numeric Template Item-L-1.5")
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

		rename_doc("Item", "Test Item for Merging 1", "Test Item for Merging 2", merge=True)

		self.assertFalse(frappe.db.exists("Item", "Test Item for Merging 1"))

		self.assertTrue(frappe.db.get_value("Bin",
			{"item_code": "Test Item for Merging 2", "warehouse": "_Test Warehouse - _TC"}))

		self.assertTrue(frappe.db.get_value("Bin",
			{"item_code": "Test Item for Merging 2", "warehouse": "_Test Warehouse 1 - _TC"}))

	def test_item_variant_by_manufacturer(self):
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
		self.assertEquals(variant.item_code, '_Test Variant Mfg-1')
		self.assertEquals(variant.description, '_Test Variant Mfg')
		self.assertEquals(variant.manufacturer, 'MSG1')
		variant.insert()

		variant = get_variant(template.name, manufacturer=manufacturer.name,
			manufacturer_part_no='007')
		self.assertEquals(variant.item_code, '_Test Variant Mfg-2')
		self.assertEquals(variant.description, '_Test Variant Mfg')
		self.assertEquals(variant.manufacturer, 'MSG1')
		self.assertEquals(variant.manufacturer_part_no, '007')


def make_item_variant():
	if not frappe.db.exists("Item", "_Test Variant Item-S"):
		variant = create_variant("_Test Variant Item", """{"Test Size": "Small"}""")
		variant.item_code = "_Test Variant Item-S"
		variant.item_name = "_Test Variant Item-S"
		variant.save()

def get_total_projected_qty(item):
	total_qty = frappe.db.sql(""" select sum(projected_qty) as projected_qty from tabBin
		where item_code = %(item)s""", {'item': item}, as_dict=1)

	return total_qty[0].projected_qty if total_qty else 0.0

test_records = frappe.get_test_records('Item')

def create_item(item_code, is_stock_item=None):
	if not frappe.db.exists("Item", item_code):
		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_name = item_code
		item.description = item_code
		item.item_group = "All Item Groups"
		item.is_stock_item = is_stock_item or 1
		item.save()

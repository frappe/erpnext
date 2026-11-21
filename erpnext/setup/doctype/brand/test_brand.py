# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

test_records = frappe.get_test_records("Brand")


class TestBrand(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_default_company_links(self):
		brand = frappe.get_doc({"doctype": "Brand", "brand": "Test Brand Defaults"})
		brand.append(
			"brand_defaults", {"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"}
		)
		brand.append("brand_defaults", {"company": "_Test Company"})
		with self.assertRaisesRegex(frappe.ValidationError, "multiple Item Defaults"):
			brand.validate()

		brand.brand_defaults.pop()
		brand.brand_defaults[0].company = "_Test Company 1"
		with self.assertRaisesRegex(frappe.ValidationError, "belong to Company"):
			brand.validate()

	def test_brand_deferred_account_and_price_defaults(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.get_item_details import get_default_deferred_account

		brand = frappe.get_doc({"doctype": "Brand", "brand": "Test Brand Propagation"})
		brand.append(
			"brand_defaults",
			{
				"company": "_Test Company",
				"default_warehouse": "_Test Warehouse - _TC",
				"deferred_revenue_account": "_Test Account Sales - _TC",
				"default_price_list": "_Test Price List",
			},
		)
		brand.insert()
		item = make_item(
			"Test Brand Propagation Item",
			{"brand": brand.name, "enable_deferred_revenue": 1, "standard_rate": 10},
		)
		self.assertEqual(
			get_default_deferred_account(
				frappe._dict(item_code=item.name, company="_Test Company"),
				item,
				"deferred_revenue_account",
			),
			"_Test Account Sales - _TC",
		)
		self.assertTrue(
			frappe.db.exists("Item Price", {"item_code": item.name, "price_list": "_Test Price List"})
		)

	@change_settings("Selling Settings", {"selling_price_list": "_Test Price List"})
	def test_inherited_price_list_matches_selling_fallback(self):
		from erpnext.stock.doctype.item.test_item import make_item

		brand = frappe.get_doc(
			{
				"doctype": "Brand",
				"brand": "Test Brand Selling Fallback",
				"brand_defaults": [
					{"company": "_Test Company 1", "default_warehouse": "_Test Warehouse 2 - _TC1"}
				],
			}
		).insert()
		item = make_item(
			properties={
				"brand": brand.name,
				"is_stock_item": 0,
				"standard_rate": 10,
				"item_defaults": [
					{
						"company": "_Test Company",
						"default_warehouse": "_Test Warehouse - _TC",
						"default_price_list": "_Test Price List",
					}
				],
			}
		)

		self.assertEqual(
			frappe.get_all("Item Price", filters={"item_code": item.name}, pluck="price_list"),
			["_Test Price List"],
		)

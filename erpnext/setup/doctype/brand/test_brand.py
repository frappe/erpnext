# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestBrand(ERPNextTestSuite):
	def test_default_company_and_inventory_account(self):
		brand = frappe.get_doc({"doctype": "Brand", "brand": "Test Brand Defaults"})
		brand.append(
			"brand_defaults", {"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"}
		)
		brand.append("brand_defaults", {"company": "_Test Company"})
		with self.assertRaisesRegex(frappe.ValidationError, "multiple Item Defaults"):
			brand.validate()

		brand.brand_defaults.pop()
		brand.brand_defaults[0].company = "_Test Company 1"
		with self.assertRaisesRegex(frappe.ValidationError, "does not belong to Company"):
			brand.validate()

		brand.brand_defaults[0].company = "_Test Company"
		brand.brand_defaults[0].default_inventory_account = "_Test Account Sales - _TC"
		with self.assertRaisesRegex(frappe.ValidationError, "must be a Stock account"):
			brand.validate()

		brand.brand_defaults[0].default_inventory_account = None
		brand.brand_defaults[0].purchase_expense_account = "_Test Account Sales - _TC"
		brand.brand_defaults[0].company = "_Test Company 1"
		brand.brand_defaults[0].default_warehouse = None
		with self.assertRaisesRegex(frappe.ValidationError, "does not belong to Company"):
			brand.validate()

	def test_brand_account_and_price_defaults(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import (
			get_manufacturing_variance_account,
			get_purchase_price_variance_account,
		)
		from erpnext.stock.get_item_details import get_default_deferred_account

		brand = frappe.get_doc({"doctype": "Brand", "brand": "Test Brand Propagation"})
		brand.append(
			"brand_defaults",
			{
				"company": "_Test Company",
				"default_warehouse": "_Test Warehouse - _TC",
				"deferred_revenue_account": "_Test Account Sales - _TC",
				"purchase_price_variance_account": "_Test Account Stock Expenses - _TC",
				"manufacturing_variance_account": "_Test Account Stock Expenses - _TC",
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
		self.assertEqual(
			get_purchase_price_variance_account(item.name, "_Test Company"),
			"_Test Account Stock Expenses - _TC",
		)
		self.assertEqual(
			get_manufacturing_variance_account(item.name, "_Test Company"),
			"_Test Account Stock Expenses - _TC",
		)
		self.assertTrue(
			frappe.db.exists("Item Price", {"item_code": item.name, "price_list": "_Test Price List"})
		)

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
		with self.change_settings("Selling Settings", selling_price_list="_Test Price List"):
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

	def test_same_named_item_group_does_not_use_unrelated_brand_defaults(self):
		from erpnext.controllers.buying_controller import get_purchase_expense_account
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.services.base_stock_gl_composer import get_expenses_added_to_stock_accounts

		name = "Test Brand Group Collision " + frappe.generate_hash(length=8)
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": name, "parent_item_group": "_Test Item Group"}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Brand",
				"brand": name,
				"brand_defaults": [
					{
						"company": "_Test Company",
						"default_warehouse": "_Test Warehouse - _TC",
						"purchase_expense_account": "_Test Account Stock Expenses - _TC",
						"expenses_added_to_stock_account": "_Test Account Stock Expenses - _TC",
					}
				],
			}
		).insert()
		other_brand = frappe.get_doc({"doctype": "Brand", "brand": name + " Other"}).insert()
		item = make_item(properties={"item_group": name, "brand": other_brand.name})

		self.assertFalse(get_purchase_expense_account(item.name, "_Test Company").purchase_expense_account)
		self.assertNotEqual(
			get_expenses_added_to_stock_accounts(item.name, "_Test Company").expenses_added_to_stock_account,
			"_Test Account Stock Expenses - _TC",
		)

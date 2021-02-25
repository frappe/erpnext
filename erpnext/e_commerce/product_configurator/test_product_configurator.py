import unittest

import frappe
from bs4 import BeautifulSoup
from frappe.utils import get_html_for_route

from erpnext.e_commerce.product_query import ProductQuery
from erpnext.e_commerce.doctype.website_item.website_item import make_website_item

test_dependencies = ["Item"]

class TestProductConfigurator(unittest.TestCase):
	def setUp(self):
		self.create_variant_item()
		self.publish_items_on_website()

	def test_product_list(self):
		usual_items = frappe.get_all('Website Item', {'published': 1, 'has_variants': 0, 'variant_of': ['is', 'not set']})
		template_items = frappe.get_all('Website Item', {'published': 1, 'has_variants': 1})
		variant_items = frappe.get_all('Website Item', {'published': 1, 'variant_of': ['is', 'set']})

		e_commerce_settings = frappe.get_doc('E Commerce Settings')
		e_commerce_settings.enable_field_filters = 1
		e_commerce_settings.append('filter_fields', {'fieldname': 'item_group'})
		e_commerce_settings.append('filter_fields', {'fieldname': 'stock_uom'})
		e_commerce_settings.save()

		html = get_html_for_route('all-products')

		soup = BeautifulSoup(html, 'html.parser')
		products_list = soup.find(class_='products-list')
		items = products_list.find_all(class_='card')

		self.assertEqual(len(items), len(template_items + variant_items + usual_items))

		items_with_item_group = frappe.get_all('Website Item', {'item_group': '_Test Item Group Desktops', 'published': 1})

		# mock query params
		frappe.form_dict = frappe._dict({
			'field_filters': '{"item_group":["_Test Item Group Desktops"]}'
		})
		html = get_html_for_route('all-products')
		soup = BeautifulSoup(html, 'html.parser')
		products_list = soup.find(class_='products-list')
		items = products_list.find_all(class_='card')
		self.assertEqual(len(items), len(items_with_item_group))


	def test_get_products_for_website(self):
		engine = ProductQuery()
		items = engine.query(attributes={
			'Test Size': ['Medium']
		})
		self.assertEqual(len(items), 1)

	def test_products_in_multiple_item_groups(self):
		"""Check if product is visible on multiple item group pages barring its own."""
		from erpnext.shopping_cart.product_query import ProductQuery

	def create_variant_item(self):
		if not frappe.db.exists('Item', '_Test Variant Item 1'):
			frappe.get_doc({
				"description": "_Test Variant Item 12",
				"doctype": "Item",
				"is_stock_item": 1,
				"variant_of": "_Test Variant Item",
				"item_code": "_Test Variant Item 1",
				"item_group": "_Test Item Group",
				"item_name": "_Test Variant Item 1",
				"stock_uom": "_Test UOM",
				"item_defaults": [{
					"company": "_Test Company",
					"default_warehouse": "_Test Warehouse - _TC",
					"expense_account": "_Test Account Cost for Goods Sold - _TC",
					"buying_cost_center": "_Test Cost Center - _TC",
					"selling_cost_center": "_Test Cost Center - _TC",
					"income_account": "Sales - _TC"
				}],
				"attributes": [
					{
						"attribute": "Test Size",
						"attribute_value": "Medium"
					}
				]
			}).insert()
		else:
			item_group_doc = frappe.get_doc("Item Group", "Tech Items")

		doc = self.create_regular_web_item("Portal Item", item_group="Tech Items")
		if not frappe.db.exists("Website Item Group", {"parent": "Portal Item"}):
			doc.append("website_item_groups", {
				"item_group": "_Test Item Group Desktops"
			})
			doc.save()

		# check if item is visible in its own Item Group's page
		engine = ProductQuery()
		items = engine.query({}, {"item_group": "Tech Items"}, None, start=0, item_group="Tech Items")
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].item_code, "Portal Item")

		# check if item is visible in configured foreign Item Group's page
		engine = ProductQuery()
		items = engine.query({}, {"item_group": "_Test Item Group Desktops"}, None, start=0, item_group="_Test Item Group Desktops")
		item_codes = [row.item_code for row in items]

	def publish_items_on_website(self):
		if frappe.db.exists("Item",  "_Test Item") and not frappe.db.exists("Website Item",  {"item_code": "_Test Item"}):
				make_website_item(frappe.get_cached_doc("Item",  "_Test Item"))

		if frappe.db.exists("Item",  "_Test Variant Item") and not frappe.db.exists("Website Item",  {"item_code": "_Test Variant Item"}):
			make_website_item(frappe.get_cached_doc("Item",  "_Test Variant Item"))

		make_website_item(frappe.get_cached_doc("Item",  "_Test Variant Item 1"))

		# teardown
		doc.delete()
		item_group_doc.delete()

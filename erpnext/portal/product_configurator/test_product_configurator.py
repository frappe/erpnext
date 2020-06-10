from __future__ import unicode_literals

from bs4 import BeautifulSoup
import frappe, unittest
from frappe.utils import set_request, get_html_for_route
from frappe.website.render import render
from erpnext.portal.product_configurator.utils import get_products_for_website
from erpnext.stock.doctype.item.test_item import make_item_variant

test_dependencies = ["Item"]

class TestProductConfigurator(unittest.TestCase):
	def setUp(self):
		self.create_variant_item()

	def test_product_list(self):
		template_items = frappe.get_all('Item', {'show_in_website': 1})
		variant_items = frappe.get_all('Item', {'show_variant_in_website': 1})

		products_settings = frappe.get_doc('Products Settings')
		products_settings.enable_field_filters = 1
		products_settings.append('filter_fields', {'fieldname': 'item_group'})
		products_settings.append('filter_fields', {'fieldname': 'stock_uom'})
		products_settings.save()

		html = get_html_for_route('all-products')

		soup = BeautifulSoup(html, 'html.parser')
		products_list = soup.find(class_='products-list')
		items = products_list.find_all(class_='card')
		self.assertEqual(len(items), len(template_items + variant_items))

		items_with_item_group = frappe.get_all('Item', {'item_group': '_Test Item Group Desktops', 'show_in_website': 1})
		variants_with_item_group = frappe.get_all('Item', {'item_group': '_Test Item Group Desktops', 'show_variant_in_website': 1})

		# mock query params
		frappe.form_dict = frappe._dict({
			'field_filters': '{"item_group":["_Test Item Group Desktops"]}'
		})
		html = get_html_for_route('all-products')
		soup = BeautifulSoup(html, 'html.parser')
		products_list = soup.find(class_='products-list')
		items = products_list.find_all(class_='card')
		self.assertEqual(len(items), len(items_with_item_group + variants_with_item_group))


	def test_get_products_for_website(self):
		items = get_products_for_website(attribute_filters={
			'Test Size': ['Medium']
		})
		self.assertEqual(len(items), 1)


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
				],
				"show_variant_in_website": 1
			}).insert()


	def tearDown(self):
		frappe.db.rollback()
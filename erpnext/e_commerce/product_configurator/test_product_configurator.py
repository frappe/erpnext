import frappe, unittest
from erpnext.e_commerce.product_data_engine.query import ProductQuery
from erpnext.e_commerce.doctype.website_item.website_item import make_website_item

test_dependencies = ["Item"]
#TODO: Rename to test item variant configurator

class TestProductConfigurator(unittest.TestCase):
	def setUp(self):
		self.create_variant_item()
		self.publish_items_on_website()

	# TODO: E-commerce server side tests
	# def test_product_list(self):
	# 	template_items = frappe.get_all('Item', {'show_in_website': 1})
	# 	variant_items = frappe.get_all('Item', {'show_variant_in_website': 1})

	# 	products_settings = frappe.get_doc('Products Settings')
	# 	products_settings.enable_field_filters = 1
	# 	products_settings.append('filter_fields', {'fieldname': 'item_group'})
	# 	products_settings.append('filter_fields', {'fieldname': 'stock_uom'})
	# 	products_settings.save()

	# 	html = get_html_for_route('all-products')

	# 	soup = BeautifulSoup(html, 'html.parser')
	# 	products_list = soup.find(class_='products-list')
	# 	items = products_list.find_all(class_='card')
	# 	self.assertEqual(len(items), len(template_items + variant_items))

	# 	items_with_item_group = frappe.get_all('Item', {'item_group': '_Test Item Group Desktops', 'show_in_website': 1})
	# 	variants_with_item_group = frappe.get_all('Item', {'item_group': '_Test Item Group Desktops', 'show_variant_in_website': 1})

	# 	# mock query params
	# 	frappe.form_dict = frappe._dict({
	# 		'field_filters': '{"item_group":["_Test Item Group Desktops"]}'
	# 	})
	# 	html = get_html_for_route('all-products')
	# 	soup = BeautifulSoup(html, 'html.parser')
	# 	products_list = soup.find(class_='products-list')
	# 	items = products_list.find_all(class_='card')
	# 	self.assertEqual(len(items), len(items_with_item_group + variants_with_item_group))


	# def test_get_products_for_website(self):
	# 	items = get_products_for_website(attribute_filters={
	# 		'Test Size': ['2XL']
	# 	})
	# 	self.assertEqual(len(items), 1)

	# def test_products_in_multiple_item_groups(self):
	# 	"""Check if product is visible on multiple item group pages barring its own."""
	# 	from erpnext.shopping_cart.product_query import ProductQuery

	# 	if not frappe.db.exists("Item Group", {"name": "Tech Items"}):
	# 		item_group_doc = frappe.get_doc({
	# 			"doctype": "Item Group",
	# 			"item_group_name": "Tech Items",
	# 			"parent_item_group": "All Item Groups",
	# 			"show_in_website": 1
	# 		}).insert()
	# 	else:
	# 		item_group_doc = frappe.get_doc("Item Group", "Tech Items")

	# 	doc = self.create_regular_web_item("Portal Item", item_group="Tech Items")
	# 	if not frappe.db.exists("Website Item Group", {"parent": "Portal Item"}):
	# 		doc.append("website_item_groups", {
	# 			"item_group": "_Test Item Group Desktops"
	# 		})
	# 		doc.save()

	# 	# check if item is visible in its own Item Group's page
	# 	engine = ProductQuery()
	# 	result = engine.query({}, {"item_group": "Tech Items"}, None, start=0, item_group="Tech Items")
	# 	items = result["items"]

	# 	self.assertEqual(len(items), 1)
	# 	self.assertEqual(items[0].item_code, "Portal Item")

	# 	# check if item is visible in configured foreign Item Group's page
	# 	engine = ProductQuery()
	# 	result = engine.query({}, {"item_group": "_Test Item Group Desktops"}, None, start=0, item_group="_Test Item Group Desktops")
	# 	items = result["items"]
	# 	item_codes = [row.item_code for row in items]

	# 	self.assertIn(len(items), [2, 3])
	# 	self.assertIn("Portal Item", item_codes)

	# 	# teardown
	# 	doc.delete()
	# 	item_group_doc.delete()

import frappe
from frappe.utils import cint
from erpnext.e_commerce.product_query import ProductQuery
from erpnext.e_commerce.filters import ProductFiltersBuilder

sitemap = 1

def get_context(context):

	if frappe.form_dict:
		search = frappe.form_dict.search
		field_filters = frappe.parse_json(frappe.form_dict.field_filters)
		attribute_filters = frappe.parse_json(frappe.form_dict.attribute_filters)
		start = cint(frappe.parse_json(frappe.form_dict.start))
	else:
		search = field_filters = attribute_filters = None
		start = 0

	engine = ProductQuery()
	context.items, discounts = engine.query(attribute_filters, field_filters, search, start)

	# Add homepage as parent
	context.parents = [{"name": frappe._("Home"), "route":"/"}]

	filter_engine = ProductFiltersBuilder()

	context.field_filters = filter_engine.get_field_filters()
	context.attribute_filters = filter_engine.get_attribute_filters()
	if discounts:
		context.discount_filters = filter_engine.get_discount_filters(discounts)

	context.e_commerce_settings = engine.settings
	context.page_length = engine.settings.products_per_page or 20

	context.no_cache = 1

@frappe.whitelist(allow_guest=True)
def get_products_html_for_website(field_filters=None, attribute_filters=None):
	"""Get Products on filter change."""
	field_filters = frappe.parse_json(field_filters)
	attribute_filters = frappe.parse_json(attribute_filters)

	engine = ProductQuery()
	items, discounts = engine.query(attribute_filters, field_filters, search_term=None, start=0)

	item_html = []
	for item in items:
		item_html.append(frappe.render_template('erpnext/www/all-products/item_row.html', {
			'item': item,
			'e_commerce_settings': None
		}))
	html = ''.join(item_html)

	if not items:
		html = frappe.render_template('erpnext/www/all-products/not_found.html', {})

	return html

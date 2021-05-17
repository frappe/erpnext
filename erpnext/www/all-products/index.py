import frappe
from frappe.utils import cint
from erpnext.e_commerce.product_query import ProductQuery
from erpnext.e_commerce.filters import ProductFiltersBuilder
from erpnext.setup.doctype.item_group.item_group import get_child_groups

sitemap = 1

def get_context(context):
	# Add homepage as parent
	context.parents = [{"name": frappe._("Home"), "route":"/"}]

	filter_engine = ProductFiltersBuilder()
	context.field_filters = filter_engine.get_field_filters()
	context.attribute_filters = filter_engine.get_attribute_filters()

	context.page_length = cint(frappe.db.get_single_value('E Commerce Settings', 'products_per_page'))or 20

	context.no_cache = 1

@frappe.whitelist(allow_guest=True)
def get_product_filter_data():
	"""Get pre-rendered filtered products and discount filters on load."""
	if frappe.form_dict:
		search = frappe.form_dict.search
		field_filters = frappe.parse_json(frappe.form_dict.field_filters)
		attribute_filters = frappe.parse_json(frappe.form_dict.attribute_filters)
		start = cint(frappe.parse_json(frappe.form_dict.start)) if frappe.form_dict.start else 0
		item_group = frappe.form_dict.item_group
	else:
		search, attribute_filters, item_group = None, None, None
		field_filters = {}
		start = 0

	sub_categories = []
	if item_group:
		field_filters['item_group'] = item_group
		sub_categories = get_child_groups(item_group)

	engine = ProductQuery()
	items, discounts = engine.query(attribute_filters, field_filters, search_term=search, start=start)

	# discount filter data
	filters = {}
	if discounts:
		filter_engine = ProductFiltersBuilder()
		filters["discount_filters"] = filter_engine.get_discount_filters(discounts)

	return items or [], filters, engine.settings, sub_categories
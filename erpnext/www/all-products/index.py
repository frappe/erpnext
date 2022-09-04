import frappe
from frappe.utils import cint

from erpnext.e_commerce.product_data_engine.filters import ProductFiltersBuilder

sitemap = 1


def get_context(context):
	# Add homepage as parent
	context.body_class = "product-page"
	context.parents = [{"name": frappe._("Home"), "route": "/"}]

	filter_engine = ProductFiltersBuilder()
	context.field_filters = filter_engine.get_field_filters()
	context.attribute_filters = filter_engine.get_attribute_filters()

	context.page_length = (
		cint(frappe.db.get_single_value("E Commerce Settings", "products_per_page")) or 20
	)

	context.no_cache = 1

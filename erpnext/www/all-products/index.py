import frappe
from erpnext.portal.product_configurator.utils import (get_products_for_website, get_product_settings,
	get_field_filter_data, get_attribute_filter_data)

sitemap = 1

def get_context(context):

	if frappe.form_dict:
		search = frappe.form_dict.search
		field_filters = frappe.parse_json(frappe.form_dict.field_filters)
		attribute_filters = frappe.parse_json(frappe.form_dict.attribute_filters)
	else:
		search = field_filters = attribute_filters = None

	context.items = get_products_for_website(field_filters, attribute_filters, search)

	product_settings = get_product_settings()
	context.field_filters = get_field_filter_data() \
		if product_settings.enable_field_filters else []

	context.attribute_filters = get_attribute_filter_data() \
		if product_settings.enable_attribute_filters else []

	context.product_settings = product_settings
	context.page_length = product_settings.products_per_page

	context.no_cache = 1

# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from erpnext.shopping_cart.product_info import get_product_info_for_website

class ProductQuery:
	"""Query engine for product listing

	Attributes:
	    cart_settings (Document): Settings for Cart
	    fields (list): Fields to fetch in query
	    filters (TYPE): Description
	    or_filters (list): Description
	    page_length (Int): Length of page for the query
	    settings (Document): Products Settings DocType
	    filters (list)
	    or_filters (list)
	"""

	def __init__(self):
		self.settings = frappe.get_doc("Products Settings")
		self.cart_settings = frappe.get_doc("Shopping Cart Settings")
		self.page_length = self.settings.products_per_page or 20
		self.fields = ['name', 'item_name', 'item_code', 'website_image', 'variant_of', 'has_variants', 'item_group', 'image', 'web_long_description', 'description', 'route']
		self.filters = []
		self.or_filters = [['show_in_website', '=', 1]]
		if not self.settings.get('hide_variants'):
			self.or_filters.append(['show_variant_in_website', '=', 1])

	def query(self, attributes=None, fields=None, search_term=None, start=0):
		"""Summary

		Args:
		    attributes (dict, optional): Item Attribute filters
		    fields (dict, optional): Field level filters
		    search_term (str, optional): Search term to lookup
		    start (int, optional): Page start

		Returns:
		    list: List of results with set fields
		"""
		if fields: self.build_fields_filters(fields)
		if search_term: self.build_search_filters(search_term)

		result = []

		if attributes:
			all_items = []
			for attribute, values in attributes.items():
				if not isinstance(values, list):
					values = [values]

				items = frappe.get_all(
					"Item",
					fields=self.fields,
					filters=[
						*self.filters,
						["Item Variant Attribute", "attribute", "=", attribute],
						["Item Variant Attribute", "attribute_value", "in", values],
					],
					or_filters=self.or_filters,
					start=start,
					limit=self.page_length
				)

				items_dict = {item.name: item for item in items}
				# TODO: Replace Variants by their parent templates

				all_items.append(set(items_dict.keys()))

			result = [items_dict.get(item) for item in list(set.intersection(*all_items))]
		else:
			result = frappe.get_all("Item", fields=self.fields, filters=self.filters, or_filters=self.or_filters, start=start, limit=self.page_length)

		for item in result:
			product_info = get_product_info_for_website(item.item_code, skip_quotation_creation=True).get('product_info')
			if product_info:
				item.formatted_price = product_info['price'].get('formatted_price') if product_info['price'] else None

		return result

	def build_fields_filters(self, filters):
		"""Build filters for field values

		Args:
		    filters (dict): Filters
		"""
		for field, values in filters.items():
			if not values:
				continue

			if isinstance(values, list):
				# If value is a list use `IN` query
				self.filters.append([field, 'IN', values])
			else:
				# `=` will be faster than `IN` for most cases
				self.filters.append([field, '=', values])

	def build_search_filters(self, search_term):
		"""Query search term in specified fields

		Args:
		    search_term (str): Search candidate
		"""
		# Default fields to search from
		default_fields = {'name', 'item_name', 'description', 'item_group'}

		# Get meta search fields
		meta = frappe.get_meta("Item")
		meta_fields = set(meta.get_search_fields())

		# Join the meta fields and default fields set
		search_fields = default_fields.union(meta_fields)
		try:
			if frappe.db.count('Item', cache=True) > 50000:
				search_fields.remove('description')
		except KeyError:
			pass

		# Build or filters for query
		search = '%{}%'.format(search_term)
		self.or_filters += [[field, 'like', search] for field in search_fields]

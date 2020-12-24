# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

class ProductQuery:
	"""Query engine for product listing
	
	Attributes:
	    cart_settings (Document): Settings for Cart
	    fields (list): Fields to fetch in query
	    filters (list)
	    or_filters (list)
	    page_length (Int): Length of page for the query
	    settings (Document): Products Settings DocType
	"""

	def __init__(self):
		self.settings = frappe.get_doc("Products Settings")
		self.cart_settings = frappe.get_doc("Shopping Cart Settings")
		self.page_length = self.settings.products_per_page or 20
		self.fields = ['name', 'item_name', 'website_image', 'variant_of', 'has_variants', 'item_group', 'image', 'web_long_description', 'description', 'route']
		self.filters = [['show_in_website', '=', 1]]
		self.or_filters = []

	def query(self, attributes=None, fields=None, search_term=None, start=0):
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
						["Item Variant Attribute", "attribute", "=", attribute],`
						["Item Variant Attribute", "attribute_value", "in", values],
					],
					or_filters=self.or_filters,
					limit=self.page_length
				)

				items_dict = {item.name: item for item in items}

				all_items.append(set(items.keys()))

			result = [items_dict.get(item) for item in list(set.intersection(*all_items))]
		else:
			result = frappe.get_all("Item", fields=self.fields, filters=self.filters, or_filters=self.or_filters, limit=self.page_length)

		return result

	def build_fields_filters(self, filters):
		for field, values in filters.items():
			if not values:
				continue
			
			if isinstance(values, list):
				self.filters.append([field, 'IN', values])
			else:
				self.filters.append([field, '=', values])

	def build_search_filters(self, search_term):
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

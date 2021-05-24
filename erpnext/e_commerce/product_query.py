# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from frappe.utils import flt

from erpnext.e_commerce.shopping_cart.product_info import get_product_info_for_website


class ProductQuery:
	"""Query engine for product listing

	Attributes:
		fields (list): Fields to fetch in query
		conditions (string): Conditions for query building
		or_conditions (string): Search conditions
		page_length (Int): Length of page for the query
		settings (Document): E Commerce Settings DocType
	"""

	def __init__(self):
		self.settings = frappe.get_doc("E Commerce Settings")
		self.page_length = self.settings.products_per_page or 20
		self.fields = ['wi.web_item_name', 'wi.name', 'wi.item_name', 'wi.item_code', 'wi.website_image', 'wi.variant_of',
			'wi.has_variants', 'wi.item_group', 'wi.image', 'wi.web_long_description', 'wi.description',
			'wi.route', 'wi.website_warehouse']
		self.conditions = ""
		self.or_conditions = ""
		self.substitutions = []

	def query(self, attributes=None, fields=None, search_term=None, start=0, item_group=None):
		"""Summary

		Args:
			attributes (dict, optional): Item Attribute filters
			fields (dict, optional): Field level filters
			search_term (str, optional): Search term to lookup
			start (int, optional): Page start

		Returns:
			list: List of results with set fields
		"""
		result, discount_list = [], []

		if fields:
			self.build_fields_filters(fields)
		if search_term:
			self.build_search_filters(search_term)
		if self.settings.hide_variants:
			self.conditions += " and wi.variant_of is null"

		if attributes:
			result = self.query_items_with_attributes(attributes, start)
		else:
			result = self.query_items(self.conditions, self.or_conditions,
				self.substitutions, start=start)

		# add price and availability info in results
		for item in result:
			product_info = get_product_info_for_website(item.item_code, skip_quotation_creation=True).get('product_info')

			if product_info and product_info['price']:
				self.get_price_discount_info(item, product_info['price'], discount_list)

			if self.settings.show_stock_availability:
				self.get_stock_availability(item)

			item.wished = False
			if frappe.db.exists("Wishlist Items", {"item_code": item.item_code, "parent": frappe.session.user}):
				item.wished = True

		discounts = []
		if discount_list:
			discounts = [min(discount_list), max(discount_list)]

		if fields and "discount" in fields:
			discount_percent = frappe.utils.flt(fields["discount"][0])
			result = [row for row in result if row.get("discount_percent") and row.discount_percent >= discount_percent]

		return result, discounts

	def get_price_discount_info(self, item, price_object, discount_list):
		"""Modify item object and add price details."""
		item.formatted_mrp = price_object.get('formatted_mrp')
		item.formatted_price = price_object.get('formatted_price')

		if price_object.get('discount_percent'):
			item.discount_percent = flt(price_object.discount_percent)
			discount_list.append(price_object.discount_percent)

		if item.formatted_mrp:
			item.discount = price_object.get('formatted_discount_percent') or \
				price_object.get('formatted_discount_rate')
		item.price = price_object.get('price_list_rate')

	def get_stock_availability(self, item):
		"""Modify item object and add stock details."""
		if item.get("website_warehouse"):
			stock_qty = frappe.utils.flt(
				frappe.db.get_value("Bin", {"item_code": item.item_code, "warehouse": item.get("website_warehouse")},
					"actual_qty"))
			item.in_stock = "green" if stock_qty else "red"
		elif not frappe.db.get_value("Item", item.item_code, "is_stock_item"):
			item.in_stock = "green" # non-stock item will always be available

	def query_items(self, conditions, or_conditions, substitutions, start=0, with_attributes=False):
		"""Build a query to fetch Website Items based on field filters."""
		self.query_fields = ", ".join(self.fields)

		attribute_table = ", `tabItem Variant Attribute` iva" if with_attributes else ""

		return frappe.db.sql(f"""
			select distinct {self.query_fields}
			from
				`tabWebsite Item` wi {attribute_table}
			where
				wi.published = 1
				{conditions}
				{or_conditions}
			limit {self.page_length} offset {start}
			""",
			tuple(substitutions),
			as_dict=1)

	def query_items_with_attributes(self, attributes, start=0):
		"""Build a query to fetch Website Items based on field & attribute filters."""
		all_items = []
		self.conditions += " and iva.parent = wi.item_code"

		for attribute, values in attributes.items():
			if not isinstance(values, list):
				values = [values]

			conditions_copy = self.conditions
			substitutions_copy = self.substitutions.copy()

			conditions_copy += " and iva.attribute = '{0}' and iva.attribute_value in ({1})" \
				.format(attribute, (", ").join(['%s'] * len(values)))
			substitutions_copy.extend(values)

			items = self.query_items(conditions_copy, self.or_conditions, substitutions_copy,
				start=start, with_attributes=True)

			items_dict = {item.name: item for item in items}
			# TODO: Replace Variants by their parent templates

			all_items.append(set(items_dict.keys()))

		result = [items_dict.get(item) for item in set.intersection(*all_items)]
		return result

	def build_fields_filters(self, filters):
		"""Build filters for field values

		Args:
			filters (dict): Filters
		"""
		for field, values in filters.items():
			if not values or field == "discount":
				continue

			# handle multiselect fields in filter addition
			meta = frappe.get_meta('Item', cached=True)
			df = meta.get_field(field)
			if df.fieldtype == 'Table MultiSelect':
				child_doctype = df.options
				child_meta = frappe.get_meta(child_doctype, cached=True)
				fields = child_meta.get("fields")
				if fields:
					self.filters.append([child_doctype, fields[0].fieldname, 'IN', values])
			elif isinstance(values, list):
				# If value is a list use `IN` query
				self.conditions += " and wi.{0} in ({1})".format(field, (', ').join(['%s'] * len(values)))
				self.substitutions.extend(values)
			else:
				# `=` will be faster than `IN` for most cases
				self.conditions += " and wi.{0} = '{1}'".format(field, values)

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
		if frappe.db.count('Item', cache=True) > 50000:
			search_fields.discard('description')

		# Build or filters for query
		search = '%{}%'.format(search_term)
		for field in search_fields:
			self.or_conditions += " or {0} like '{1}'".format(field, search)

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
		self.fields = ['web_item_name', 'name', 'item_name', 'item_code', 'website_image',
			'variant_of', 'has_variants', 'item_group', 'image', 'web_long_description',
			'short_description', 'route', 'website_warehouse', 'ranking']
		self.filters = [["published", "=", 1]]
		self.or_filters = []

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
		website_item_groups = []

		# if from item group page consider website item group table
		if item_group:
			website_item_groups = frappe.db.get_all(
				"Website Item",
				fields=self.fields + ["`tabWebsite Item Group`.parent as wig_parent"],
				filters=[["Website Item Group", "item_group", "=", item_group]]
			)

		if fields:
			self.build_fields_filters(fields)
		if search_term:
			self.build_search_filters(search_term)
		if self.settings.hide_variants:
			self.filters.append(["variant_of", "is", "not set"])

		count = 0
		if attributes:
			result, count = self.query_items_with_attributes(attributes, start)
		else:
			result, count = self.query_items(start=start)

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

		return {
			"items": result,
			"items_count": count,
			"discounts": discounts
		}

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

	def query_items(self, start=0):
		"""Build a query to fetch Website Items based on field filters."""
		# MySQL does not support offset without limit,
		# frappe does not accept two parameters for limit
		# https://dev.mysql.com/doc/refman/8.0/en/select.html#id4651989
		count_items = frappe.db.get_all(
			"Website Item",
			filters=self.filters,
			or_filters=self.or_filters,
			limit_page_length=184467440737095516,
			limit_start=start, # get all items from this offset for total count ahead
			order_by="ranking desc")
		count = len(count_items)

		items = frappe.db.get_all(
			"Website Item",
			fields=self.fields,
			filters=self.filters,
			or_filters=self.or_filters,
			limit_page_length=self.page_length,
			limit_start=start,
			order_by="ranking desc")

		return items, count

	def query_items_with_attributes(self, attributes, start=0):
		"""Build a query to fetch Website Items based on field & attribute filters."""
		item_codes = []

		for attribute, values in attributes.items():
			if not isinstance(values, list):
				values = [values]

			# get items that have selected attribute & value
			item_code_list = frappe.db.get_all(
				"Item",
				fields=["item_code"],
				filters=[
					["published_in_website", "=", 1],
					["Item Variant Attribute", "attribute", "=", attribute],
					["Item Variant Attribute", "attribute_value", "in", values]
				])
			item_codes.append({x.item_code for x in item_code_list})

		if item_codes:
			item_codes = list(set.intersection(*item_codes))
			self.filters.append(["item_code", "in", item_codes])

		items, count = self.query_items(start=start)

		return items, count

	def build_fields_filters(self, filters):
		"""Build filters for field values

		Args:
			filters (dict): Filters
		"""
		for field, values in filters.items():
			if not values or field == "discount":
				continue

			# handle multiselect fields in filter addition
			meta = frappe.get_meta('Website Item', cached=True)
			df = meta.get_field(field)
			if df.fieldtype == 'Table MultiSelect':
				child_doctype = df.options
				child_meta = frappe.get_meta(child_doctype, cached=True)
				fields = child_meta.get("fields")
				if fields:
					self.filters.append([child_doctype, fields[0].fieldname, 'IN', values])
			elif isinstance(values, list):
				# If value is a list use `IN` query
				self.filters.append([field, "in", values])
			else:
				# `=` will be faster than `IN` for most cases
				self.filters.append([field, "=", values])

	def build_search_filters(self, search_term):
		"""Query search term in specified fields

		Args:
			search_term (str): Search candidate
		"""
		# Default fields to search from
		default_fields = {'item_code', 'item_name', 'web_long_description', 'item_group'}

		# Get meta search fields
		meta = frappe.get_meta("Website Item")
		meta_fields = set(meta.get_search_fields())

		# Join the meta fields and default fields set
		search_fields = default_fields.union(meta_fields)
		if frappe.db.count('Website Item', cache=True) > 50000:
			search_fields.discard('web_long_description')

		# Build or filters for query
		search = '%{}%'.format(search_term)
		for field in search_fields:
			self.or_filters.append([field, "like", search])

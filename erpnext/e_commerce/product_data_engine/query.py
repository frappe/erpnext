# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt
from erpnext.e_commerce.shopping_cart.product_info import get_product_info_for_website
from erpnext.e_commerce.doctype.item_review.item_review import get_customer
from erpnext.utilities.product import get_non_stock_item_status

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

		self.or_filters = []
		self.filters = [["published", "=", 1]]
		self.fields = ['web_item_name', 'name', 'item_name', 'item_code', 'website_image',
			'variant_of', 'has_variants', 'item_group', 'image', 'web_long_description',
			'short_description', 'route', 'website_warehouse', 'ranking']

	def query(self, attributes=None, fields=None, search_term=None, start=0, item_group=None):
		"""
		Args:
			attributes (dict, optional): Item Attribute filters
			fields (dict, optional): Field level filters
			search_term (str, optional): Search term to lookup
			start (int, optional): Page start

		Returns:
			dict: Dict containing items, item count & discount range
		"""
		# track if discounts included in field filters
		self.filter_with_discount = bool(fields.get("discount"))
		result, discount_list, website_item_groups, cart_items, count = [], [], [], [], 0

		website_item_groups = self.get_website_item_group_results(item_group, website_item_groups)

		if fields:
			self.build_fields_filters(fields)
		if search_term:
			self.build_search_filters(search_term)
		if self.settings.hide_variants:
			self.filters.append(["variant_of", "is", "not set"])

		# query results
		if attributes:
			result, count = self.query_items_with_attributes(attributes, start)
		else:
			result, count = self.query_items(start=start)

		result = self.combine_web_item_group_results(item_group, result, website_item_groups)

		# sort combined results by ranking
		result = sorted(result, key=lambda x: x.get("ranking"), reverse=True)

		if self.settings.enabled:
			cart_items = self.get_cart_items()

		result, discount_list = self.add_display_details(result, discount_list, cart_items)

		discounts = []
		if discount_list:
			discounts = [min(discount_list), max(discount_list)]

		result = self.filter_results_by_discount(fields, result)

		return {
			"items": result,
			"items_count": count,
			"discounts": discounts
		}

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

		# If discounts included, return all rows.
		# Slice after filtering rows with discount (See `filter_results_by_discount`).
		# Slicing before hand will miss discounted items on the 3rd or 4th page.
		# Discounts are fetched on computing Pricing Rules so we cannot query them directly.
		page_length = 184467440737095516 if self.filter_with_discount else self.page_length

		items = frappe.db.get_all(
			"Website Item",
			fields=self.fields,
			filters=self.filters,
			or_filters=self.or_filters,
			limit_page_length=page_length,
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

	def get_website_item_group_results(self, item_group, website_item_groups):
		"""Get Web Items for Item Group Page via Website Item Groups."""
		if item_group:
			website_item_groups = frappe.db.get_all(
				"Website Item",
				fields=self.fields + ["`tabWebsite Item Group`.parent as wig_parent"],
				filters=[["Website Item Group", "item_group", "=", item_group]]
			)
		return website_item_groups

	def add_display_details(self, result, discount_list, cart_items):
		"""Add price and availability details in result."""
		for item in result:
			product_info = get_product_info_for_website(item.item_code, skip_quotation_creation=True).get('product_info')

			if product_info and product_info['price']:
				# update/mutate item and discount_list objects
				self.get_price_discount_info(item, product_info['price'], discount_list)

			if self.settings.show_stock_availability:
				self.get_stock_availability(item)

			item.in_cart = item.item_code in cart_items

			item.wished = False
			if frappe.db.exists("Wishlist Item", {"item_code": item.item_code, "parent": frappe.session.user}):
				item.wished = True

		return result, discount_list

	def get_price_discount_info(self, item, price_object, discount_list):
		"""Modify item object and add price details."""
		fields = ["formatted_mrp", "formatted_price", "price_list_rate"]
		for field in fields:
			item[field] = price_object.get(field)

		if price_object.get('discount_percent'):
			item.discount_percent = flt(price_object.discount_percent)
			discount_list.append(price_object.discount_percent)

		if item.formatted_mrp:
			item.discount = price_object.get('formatted_discount_percent') or \
				price_object.get('formatted_discount_rate')

	def get_stock_availability(self, item):
		"""Modify item object and add stock details."""
		item.in_stock = False
		warehouse = item.get("website_warehouse")
		is_stock_item = frappe.get_cached_value("Item", item.item_code, "is_stock_item")

		if not is_stock_item:
			if warehouse:
				# product bundle case
				item.in_stock = get_non_stock_item_status(item.item_code, "website_warehouse")
			else:
				item.in_stock = True
		elif warehouse:
			# stock item and has warehouse
			actual_qty = frappe.db.get_value(
				"Bin",
				{"item_code": item.item_code,"warehouse": item.get("website_warehouse")},
				"actual_qty")
			item.in_stock = bool(flt(actual_qty))

	def get_cart_items(self):
		customer = get_customer(silent=True)
		if customer:
			quotation = frappe.get_all("Quotation", fields=["name"], filters=
				{"party_name": customer, "order_type": "Shopping Cart", "docstatus": 0},
				order_by="modified desc", limit_page_length=1)
			if quotation:
				items = frappe.get_all(
					"Quotation Item",
					fields=["item_code"],
					filters={
						"parent": quotation[0].get("name")
					})
				items = [row.item_code for row in items]
				return items

		return []

	def combine_web_item_group_results(self, item_group, result, website_item_groups):
		"""Combine results with context of website item groups into item results."""
		if item_group and website_item_groups:
			items_list = {row.name for row in result}
			for row in website_item_groups:
				if row.wig_parent not in items_list:
					result.append(row)

		return result

	def filter_results_by_discount(self, fields, result):
		if fields and fields.get("discount"):
			discount_percent = frappe.utils.flt(fields["discount"][0])
			result = [row for row in result if row.get("discount_percent") and row.discount_percent >= discount_percent]

		if self.filter_with_discount:
			# no limit was added to results while querying
			# slice results manually
			result[:self.page_length]

		return result
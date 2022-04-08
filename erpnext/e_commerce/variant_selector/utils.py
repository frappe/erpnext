import frappe
from frappe.utils import cint

from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	get_shopping_cart_settings,
)
from erpnext.e_commerce.shopping_cart.cart import _set_price_list
from erpnext.e_commerce.variant_selector.item_variants_cache import ItemVariantsCacheManager
from erpnext.utilities.product import get_price


def get_item_codes_by_attributes(attribute_filters, template_item_code=None):
	items = []

	for attribute, values in attribute_filters.items():
		attribute_values = values

		if not isinstance(attribute_values, list):
			attribute_values = [attribute_values]

		if not attribute_values:
			continue

		wheres = []
		query_values = []
		for attribute_value in attribute_values:
			wheres.append("( attribute = %s and attribute_value = %s )")
			query_values += [attribute, attribute_value]

		attribute_query = " or ".join(wheres)

		if template_item_code:
			variant_of_query = "AND t2.variant_of = %s"
			query_values.append(template_item_code)
		else:
			variant_of_query = ""

		query = """
			SELECT
				t1.parent
			FROM
				`tabItem Variant Attribute` t1
			WHERE
				1 = 1
				AND (
					{attribute_query}
				)
				AND EXISTS (
					SELECT
						1
					FROM
						`tabItem` t2
					WHERE
						t2.name = t1.parent
						{variant_of_query}
				)
			GROUP BY
				t1.parent
			ORDER BY
				NULL
		""".format(
			attribute_query=attribute_query, variant_of_query=variant_of_query
		)

		item_codes = set([r[0] for r in frappe.db.sql(query, query_values)])  # nosemgrep
		items.append(item_codes)

	res = list(set.intersection(*items))

	return res


@frappe.whitelist(allow_guest=True)
def get_attributes_and_values(item_code):
	"""Build a list of attributes and their possible values.
	This will ignore the values upon selection of which there cannot exist one item.
	"""
	item_cache = ItemVariantsCacheManager(item_code)
	item_variants_data = item_cache.get_item_variants_data()

	attributes = get_item_attributes(item_code)
	attribute_list = [a.attribute for a in attributes]

	valid_options = {}
	for item_code, attribute, attribute_value in item_variants_data:
		if attribute in attribute_list:
			valid_options.setdefault(attribute, set()).add(attribute_value)

	item_attribute_values = frappe.db.get_all(
		"Item Attribute Value", ["parent", "attribute_value", "idx"], order_by="parent asc, idx asc"
	)
	ordered_attribute_value_map = frappe._dict()
	for iv in item_attribute_values:
		ordered_attribute_value_map.setdefault(iv.parent, []).append(iv.attribute_value)

	# build attribute values in idx order
	for attr in attributes:
		valid_attribute_values = valid_options.get(attr.attribute, [])
		ordered_values = ordered_attribute_value_map.get(attr.attribute, [])
		attr["values"] = [v for v in ordered_values if v in valid_attribute_values]

	return attributes


@frappe.whitelist(allow_guest=True)
def get_next_attribute_and_values(item_code, selected_attributes):
	"""Find the count of Items that match the selected attributes.
	Also, find the attribute values that are not applicable for further searching.
	If less than equal to 10 items are found, return item_codes of those items.
	If one item is matched exactly, return item_code of that item.
	"""
	selected_attributes = frappe.parse_json(selected_attributes)

	item_cache = ItemVariantsCacheManager(item_code)
	item_variants_data = item_cache.get_item_variants_data()

	attributes = get_item_attributes(item_code)
	attribute_list = [a.attribute for a in attributes]
	filtered_items = get_items_with_selected_attributes(item_code, selected_attributes)

	next_attribute = None

	for attribute in attribute_list:
		if attribute not in selected_attributes:
			next_attribute = attribute
			break

	valid_options_for_attributes = frappe._dict()

	for a in attribute_list:
		valid_options_for_attributes[a] = set()

		selected_attribute = selected_attributes.get(a, None)
		if selected_attribute:
			# already selected attribute values are valid options
			valid_options_for_attributes[a].add(selected_attribute)

	for row in item_variants_data:
		item_code, attribute, attribute_value = row
		if (
			item_code in filtered_items
			and attribute not in selected_attributes
			and attribute in attribute_list
		):
			valid_options_for_attributes[attribute].add(attribute_value)

	optional_attributes = item_cache.get_optional_attributes()
	exact_match = []
	# search for exact match if all selected attributes are required attributes
	if len(selected_attributes.keys()) >= (len(attribute_list) - len(optional_attributes)):
		item_attribute_value_map = item_cache.get_item_attribute_value_map()
		for item_code, attr_dict in item_attribute_value_map.items():
			if item_code in filtered_items and set(attr_dict.keys()) == set(selected_attributes.keys()):
				exact_match.append(item_code)

	filtered_items_count = len(filtered_items)

	# get product info if exact match
	# from erpnext.e_commerce.shopping_cart.product_info import get_product_info_for_website
	if exact_match:
		cart_settings = get_shopping_cart_settings()
		product_info = get_item_variant_price_dict(exact_match[0], cart_settings)

		if product_info:
			product_info["allow_items_not_in_stock"] = cint(cart_settings.allow_items_not_in_stock)
	else:
		product_info = None

	return {
		"next_attribute": next_attribute,
		"valid_options_for_attributes": valid_options_for_attributes,
		"filtered_items_count": filtered_items_count,
		"filtered_items": filtered_items if filtered_items_count < 10 else [],
		"exact_match": exact_match,
		"product_info": product_info,
	}


def get_items_with_selected_attributes(item_code, selected_attributes):
	item_cache = ItemVariantsCacheManager(item_code)
	attribute_value_item_map = item_cache.get_attribute_value_item_map()

	items = []
	for attribute, value in selected_attributes.items():
		filtered_items = attribute_value_item_map.get((attribute, value), [])
		items.append(set(filtered_items))

	return set.intersection(*items)


# utilities


def get_item_attributes(item_code):
	attributes = frappe.db.get_all(
		"Item Variant Attribute",
		fields=["attribute"],
		filters={"parenttype": "Item", "parent": item_code},
		order_by="idx asc",
	)

	optional_attributes = ItemVariantsCacheManager(item_code).get_optional_attributes()

	for a in attributes:
		if a.attribute in optional_attributes:
			a.optional = True

	return attributes


def get_item_variant_price_dict(item_code, cart_settings):
	if cart_settings.enabled and cart_settings.show_price:
		is_guest = frappe.session.user == "Guest"
		# Show Price if logged in.
		# If not logged in, check if price is hidden for guest.
		if not is_guest or not cart_settings.hide_price_for_guest:
			price_list = _set_price_list(cart_settings, None)
			price = get_price(
				item_code, price_list, cart_settings.default_customer_group, cart_settings.company
			)
			return {"price": price}

	return None

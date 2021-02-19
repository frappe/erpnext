import frappe
from frappe.utils import cint
from erpnext.portal.product_configurator.item_variants_cache import ItemVariantsCacheManager
from erpnext.shopping_cart.product_info import get_product_info_for_website

@frappe.whitelist(allow_guest=True)
def get_attributes_and_values(item_code):
	'''Build a list of attributes and their possible values.
	This will ignore the values upon selection of which there cannot exist one item.
	'''
	item_cache = ItemVariantsCacheManager(item_code)
	item_variants_data = item_cache.get_item_variants_data()

	attributes = get_item_attributes(item_code)
	attribute_list = [a.attribute for a in attributes]

	valid_options = {}
	for item_code, attribute, attribute_value in item_variants_data:
		if attribute in attribute_list:
			valid_options.setdefault(attribute, set()).add(attribute_value)

	item_attribute_values = frappe.db.get_all('Item Attribute Value',
		['parent', 'attribute_value', 'idx'], order_by='parent asc, idx asc')
	ordered_attribute_value_map = frappe._dict()
	for iv in item_attribute_values:
		ordered_attribute_value_map.setdefault(iv.parent, []).append(iv.attribute_value)

	# build attribute values in idx order
	for attr in attributes:
		valid_attribute_values = valid_options.get(attr.attribute, [])
		ordered_values = ordered_attribute_value_map.get(attr.attribute, [])
		attr['values'] = [v for v in ordered_values if v in valid_attribute_values]

	return attributes


@frappe.whitelist(allow_guest=True)
def get_next_attribute_and_values(item_code, selected_attributes):
	'''Find the count of Items that match the selected attributes.
	Also, find the attribute values that are not applicable for further searching.
	If less than equal to 10 items are found, return item_codes of those items.
	If one item is matched exactly, return item_code of that item.
	'''
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

	valid_options_for_attributes = frappe._dict({})

	for a in attribute_list:
		valid_options_for_attributes[a] = set()

		selected_attribute = selected_attributes.get(a, None)
		if selected_attribute:
			# already selected attribute values are valid options
			valid_options_for_attributes[a].add(selected_attribute)

	for row in item_variants_data:
		item_code, attribute, attribute_value = row
		if item_code in filtered_items and attribute not in selected_attributes and attribute in attribute_list:
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
	from erpnext.shopping_cart.product_info import get_product_info_for_website
	if exact_match:
		data = get_product_info_for_website(exact_match[0])
		product_info = data.product_info
		if product_info:
			product_info["allow_items_not_in_stock"] = cint(data.cart_settings.allow_items_not_in_stock)
		if not data.cart_settings.show_price:
			product_info = None
	else:
		product_info = None

	return {
		'next_attribute': next_attribute,
		'valid_options_for_attributes': valid_options_for_attributes,
		'filtered_items_count': filtered_items_count,
		'filtered_items': filtered_items if filtered_items_count < 10 else [],
		'exact_match': exact_match,
		'product_info': product_info
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
	attributes = frappe.db.get_all('Item Variant Attribute',
		fields=['attribute'],
		filters={
			'parenttype': 'Item',
			'parent': item_code
		},
		order_by='idx asc'
	)

	optional_attributes = ItemVariantsCacheManager(item_code).get_optional_attributes()

	for a in attributes:
		if a.attribute in optional_attributes:
			a.optional = True

	return attributes


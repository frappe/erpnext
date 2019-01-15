import json
import frappe
from .item_variants_cache import ItemVariantsCacheManager

def get_context(context):
	context.items = get_products_for_website()

	product_settings = frappe.get_cached_doc('Products Settings')
	context.field_filters = get_field_filter_data() \
		if product_settings.enable_field_filters else []

	context.attribute_filters = get_attribute_filter_data() \
		if product_settings.enable_attribute_filters else []

	context.product_settings = product_settings
	context.page_length = product_settings.products_per_page


def get_field_filter_data():
	product_settings = frappe.get_cached_doc('Products Settings')
	filter_fields = [row.fieldname for row in product_settings.filter_fields]

	meta = frappe.get_meta('Item')
	fields = [df for df in meta.fields if df.fieldname in filter_fields]

	filter_data = []
	for f in fields:
		doctype = f.options
		values = [d.name for d in frappe.get_all(doctype)]
		filter_data.append([f, values])

	return filter_data


def get_attribute_filter_data():
	product_settings = frappe.get_cached_doc('Products Settings')
	attributes = [row.attribute for row in product_settings.filter_attributes]
	attribute_docs = [
		frappe.get_doc('Item Attribute', attribute) for attribute in attributes
	]

	# mark attribute values as checked if they are present in the request url
	if frappe.form_dict:
		for attr in attribute_docs:
			if attr.name in frappe.form_dict:
				value = frappe.form_dict[attr.name]
				if value:
					enabled_values = value.split(',')
				else:
					enabled_values = []

				for v in enabled_values:
					for item_attribute_row in attr.item_attribute_values:
						if v == item_attribute_row.attribute_value:
							item_attribute_row.checked = True

	return attribute_docs


def get_products_for_website(field_filters=None, attribute_filters=None):
	search = None

	if not (field_filters or attribute_filters):
		if frappe.form_dict:
			search = frappe.form_dict.search
			field_filters = frappe.parse_json(frappe.form_dict.field_filters)
			attribute_filters = frappe.parse_json(frappe.form_dict.attribute_filters)

	if attribute_filters:
		item_codes = get_item_codes_by_attributes(attribute_filters)

		items_by_attributes = get_items({
			'name': ['in', item_codes],
			'show_variant_in_website': 1
		})

	if field_filters:
		items_by_fields = get_items_by_fields(field_filters)

	if attribute_filters and not field_filters:
		return items_by_attributes

	if field_filters and not attribute_filters:
		return items_by_fields

	if field_filters and attribute_filters:
		items_intersection = []
		item_codes_in_attribute = [item.name for item in items_by_attributes]

		for item in items_by_fields:
			if item.name in item_codes_in_attribute:
				items_intersection.append(item)

		return items_intersection

	if search:
		search = '%' + search + '%'
		return get_items(or_filters={
			'name': ['like', search],
			'item_name': ['like', search],
			'description': ['like', search],
			'item_group': ['like', search]
		})

	return get_items()


@frappe.whitelist(allow_guest=True)
def get_products_html_for_website(field_filters=None, attribute_filters=None):
	field_filters = frappe.parse_json(field_filters)
	attribute_filters = frappe.parse_json(attribute_filters)

	items = get_products_for_website(field_filters, attribute_filters)
	html = ''.join(get_html_for_items(items))

	if not items:
		html = frappe.render_template('erpnext/www/products/not_found.html', {})

	return html


@frappe.whitelist(allow_guest=True)
def get_items_by_attributes(attribute_filters, template_item_code=None):
	attribute_filters = frappe.parse_json(attribute_filters)

	for attribute, value in attribute_filters.items():
		attribute_filters[attribute] = [value]

	item_codes = get_item_codes_by_attributes(attribute_filters, template_item_code)
	# items = get_items({
	# 	'name': ['in', item_codes]
	# })

	return item_codes

	# return ''.join(get_html_for_items(items))


@frappe.whitelist(allow_guest=True)
def get_item_codes_by_attributes(attribute_filters, template_item_code=None):
	items = []

	for attribute, values in attribute_filters.iteritems():
		attribute_values = values

		if not attribute_values: continue

		wheres = []
		query_values = []
		for attribute_value in attribute_values:
			wheres.append('( attribute = %s and attribute_value = %s )')
			query_values += [attribute, attribute_value]

		attribute_query = ' or '.join(wheres)

		if template_item_code:
			variant_of_query = 'AND t2.variant_of = %s'
			query_values.append(template_item_code)
		else:
			variant_of_query = ''

		# query = '''
		# 	select
		# 		parent
		# 	from `tabItem Variant Attribute`
		# 	where
		# 		 {variant_query}
		# 	group by parent
		# '''.format(where=where, variant_query=variant_query)

		query = '''
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
		'''.format(attribute_query=attribute_query, variant_of_query=variant_of_query)

		print(query)

		item_codes = set([r[0] for r in frappe.db.sql(query, query_values)])
		items.append(item_codes)

	res = list(set.intersection(*items))

	return res


@frappe.whitelist(allow_guest=True)
def get_attributes_and_values(item_code):
	item_cache = ItemVariantsCacheManager(item_code)
	item_variants_data = item_cache.get_item_variants_data()

	attributes = get_item_attributes(item_code)
	attribute_list = [a.attribute for a in attributes]

	attribute_values = frappe.db.get_all('Item Attribute Value',
		filters={'parent': ['in', attribute_list]},
		fields=['parent as attribute', 'attribute_value'],
		order_by='idx asc')

	for a in attribute_values:
		for attr in attributes:
			if attr.attribute == a.attribute:
				attr.setdefault('values', []).append(a.attribute_value)

	valid_options = {}
	for item_code, attribute, attribute_value in item_variants_data:
		if attribute in attribute_list:
			valid_options.setdefault(attribute, set()).add(attribute_value)

	for attr in attributes:
		attr['valid_values'] = valid_options.get(attr.attribute, [])

	return attributes


@frappe.whitelist(allow_guest=True)
def get_next_attribute_and_values(item_code, selected_attributes):
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

	for row in item_variants_data:
		item_code, attribute, attribute_value = row
		if item_code in filtered_items and attribute not in selected_attributes and attribute in attribute_list:
			valid_options_for_attributes.setdefault(attribute, set()).add(attribute_value)

	optional_attributes = item_cache.get_optional_attributes()
	exact_match = []
	# search for exact match if all selected attributes are required attributes
	if len(selected_attributes.keys()) >= (len(attribute_list) - len(optional_attributes)):
		item_attribute_value_map = item_cache.get_item_attribute_value_map()
		for item_code, attr_dict in item_attribute_value_map.items():
			if item_code in filtered_items and set(attr_dict.keys()) == set(selected_attributes.keys()):
				exact_match.append(item_code)

	filtered_items_count = len(filtered_items)

	return {
		'next_attribute': next_attribute,
		'valid_options_for_attributes': valid_options_for_attributes,
		'filtered_items_count': filtered_items_count,
		'filtered_items': filtered_items if filtered_items_count < 10 else [],
		'exact_match': exact_match
	}


def get_items_with_selected_attributes(item_code, selected_attributes):
	item_cache = ItemVariantsCacheManager(item_code)
	attribute_value_item_map = item_cache.get_attribute_value_item_map()

	items = []
	for attribute, value in selected_attributes.items():
		items.append(set(attribute_value_item_map[(attribute, value)]))

	return set.intersection(*items)


def get_items_by_fields(field_filters):
	filters = frappe._dict({})
	for fieldname, values in field_filters.iteritems():
		if not values: continue
		if len(values) == 1:
			filters[fieldname] = values[0]
		else:
			filters[fieldname] = ['in', values]

	return get_items(filters)


def get_items(filters=None, or_filters=None):
	if not filters and not or_filters:
		filters = {'variant_of': '', 'show_in_website': 1}

	start = frappe.form_dict.start or 0
	page_length = frappe.db.get_single_value('Products Settings', 'products_per_page')

	return frappe.get_all('Item',
		fields=['name', 'item_name', 'image', 'route', 'description'],
		filters=filters,
		or_filters=or_filters,
		start=start,
		page_length=page_length
	)


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

	reqd_attributes = []
	opt_attributes = []

	for a in attributes:
		if a.attribute in optional_attributes:
			a.optional = True
			opt_attributes.append(a)
		else:
			reqd_attributes.append(a)

	return reqd_attributes + opt_attributes

def get_html_for_items(items):
	html = []
	for item in items:
		html.append(frappe.render_template('erpnext/www/products/item_row.html', {
			'item': item
		}))
	return html
